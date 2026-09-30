# `good_fundamental_scan` -- market-wide fundamental screener

Filters the US stock market down to candidates with sound fundamentals, then scores every
candidate with the `/fundamental-check` skill's own Quality/Risk gauntlet. One command, one
output file, no LLM in the loop.

## Running it

**Default (no flags): top 150 by market cap, not the whole market.**

```bash
python tools/skills/good_fundamental_scan/scan.py
```
 
`filter.json`'s Finviz filters are used to pre-scan the market for reasnable stocks.
currently match roughly 900 US tickers at any given time.
a plain `python scan.py`does **not** run the fundamental check on all of them. 
It sorts that Finviz-filtered universe by `--order` (default `Market Cap.`, largest first) 
and only deep-checks the top `--limit` (default 150). 


**`--full-market` (or `--limit 0`): 

```bash
python tools/skills/good_fundamental_scan/scan.py --limit 60
python tools/skills/good_fundamental_scan/scan.py --full-market
```
This runs the fundamental check on the entire `filter.json`-matched universe, 
not just the largest names. Useful when you don't want size to bias which "good fundamentals" names surface.

**`other cli options: 

```bash
python tools/skills/good_fundamental_scan/scan.py --tickers AAPL,MSFT,NVDA
python tools/skills/good_fundamental_scan/scan.py --min-quality 60 --max-risk 40
python tools/skills/good_fundamental_scan/scan.py --workers 4 --out reports/custom.html
```

- `--limit` -- how many Finviz candidates get the full fundamental check (default 150).
  Each check is a slow, network-heavy subprocess (several yfinance calls with retry/backoff),
  so this is a speed/coverage knob, not a quality filter -- Finviz already sorts by `--order`
  (default `Market Cap.`, largest first) before truncating. `--limit 0` is the same as
  `--full-market`.
- `--full-market` -- run the pre-screen with no cap at all, over every ticker `filter.json`
  matches market-wide. The run prints `Pre-screen found N candidates.` as soon as Finviz returns,
  before any fundamental checks start, so you know the scope before committing to the runtime --
  a full-market run can be many hundreds of candidates and take hours at the default `--workers`.
- `--tickers` -- skip Finviz entirely and check exactly this comma-separated list (also skips
  saving `results/filter_<date>.csv`, since no Finviz screen runs).
- `--workers` -- parallel `fundamental_check.py` subprocesses (default 4 -- yfinance rate-limits
  harder under concurrent load, so pushing this higher can make a run slower, not faster; each
  check gets a 300s subprocess timeout to absorb that).
- `--min-quality` / `--max-risk` -- the "good fundamentals" bar used for the report's PASS
  column (defaults 55 / 45 -- see `fundamental-check`'s own `band_quality`/`band_risk` for what
  those numbers mean: Quality 55 sits inside "Mixed", so raise it if you want only "Solid"+).
- `--filters` -- path to a different Finviz filters JSON (default `filter.json` beside this
  script).
- `--order` -- Finviz sort column applied before `--limit` truncates (default `Market Cap.`).
- `--view` -- Finviz screener view saved to `results/filter_<date>.csv` (default `overview` --
  company/sector/market cap/P-E; see `fetch-finviz-stocks-screener`'s own `--view` for the other
  choices).
- `--candidates-out` -- write the pre-filter candidate list, one ticker per line, to this path
  (default `reports/candidates_<date>.txt`; pass `""` to skip writing it). This is a plain-text
  convenience duplicate of the `Ticker` column already in `results/filter_<date>.csv` -- written
  as soon as the Finviz screen returns, before the slow per-ticker checks start, so it survives
  even if the run is interrupted partway through.
- `--no-browser` -- by default, the finished HTML report is opened automatically in whatever
  program Windows has associated with `.html` (`os.startfile`) as the very last step. Pass this
  flag to skip that (e.g. running headless, on a schedule, or over SSH).

## What it does

1. **Pre-screen (Finviz, via the `fetch-finviz-stocks-screener` skill), saved as
   `results/filter_<date>.csv`.** Same convention every other `screener/<slug>` folder in this
   repo uses (`run_scan.py --out-dir`): a commented header block (source, exact filter dict, view,
   order, scan date, the exact command to reproduce it) above the full Finviz row data. `filter.json`
   narrows the whole market to a tradable, plausibly-sound candidate list before anything slow
   runs. Every filter here is chosen against one question: *could this exclude a name that
   `fundamental_check.py` would not itself judge unfit?* -- not "does it look like the closest
   Finviz bucket to the real threshold". Finviz's buckets are coarse, so the closest-looking
   option is often stricter than the real check and silently drops names that would have passed.

   **Matches an actual AVOID gate -- zero restriction risk, since anything excluded here would
   AVOID in `fundamental_check.py` regardless:**

   | Finviz filter | Value | Why |
   |---|---|---|
   | Price | Over $2 | exact match to the tradability AVOID gate |
   | Market Cap. | +Micro (over $50mln) | the real gate is $100M; Finviz has no $100M bucket, and the previously-used `+Small (over $300mln)` wrongly excluded genuine $100M-$300M passes. `+Micro` is the loosest bucket at or below the real floor |
   | Average Volume | Over 100K | proxies the $1M/day dollar-volume gate, which Finviz can't filter on directly (share count only, not price x volume) -- loosened from 300K so a higher-priced, lower-share-count name that clears $1M/day isn't dropped on share count alone |
   | Return on Equity | Positive (>0%) | redundant with the critical `neg_equity` gate: net income > 0 (required by the P/E filter below) with equity > 0 already implies ROE > 0, so this only ever excludes names that would AVOID anyway |

   **No matching AVOID gate exists for these -- each is a scored/weighted check, not a hard gate,
   so any Finviz threshold here is a real tradeoff between search-space size and recall. Kept at
   the loosest bucket that still narrows anything, rather than the bucket closest to the check's
   actual PASS threshold:**

   | Finviz filter | Value | The real (non-critical) check | Why this bucket, not a tighter one |
   |---|---|---|---|
   | P/E | Profitable (>0) | -- | deliberate scope choice, not a granularity fix: this excludes the `pre_revenue` rulebook's own companies (revenue < $25M, negative earnings) from this "good fundamentals" screen entirely |
   | Operating Margin | Positive (>0%) | `op_margin` PASS bar is 10% | left at the loosest notch -- tightening to 10% would exclude names that miss this one scored check but still clear the overall Quality bar on other pillars |
   | Quick Ratio | Over 0.5 | `quick` PASS bar is 1.0, with a WATCH-waiver when CFO covers >50% of current liabilities | 0.5 isn't an arbitrary midpoint -- it's the exact number the check's own waiver uses, so a company living in that waiver zone still gets through the pre-screen |
   | Current Ratio | Over 1 | `current` PASS bar is 1.2, closest Finviz bucket is 1.5 | one bucket looser than the closest match, so as not to cut further into names the real check might still pass or WATCH-waive |
   | Sales growth qtr over qtr | Positive (>0%) | `rev_growth` PASS bar is 5%, measured latest-quarter-vs-same-quarter-last-year | this Finviz filter is the actual same comparison `rev_growth` computes (not "EPS growth this year", used previously, which measures a different line item); kept at the loose end since it's a scored, not critical, check |

   **Dropped:** `Debt/Equity`. The check's real bar is 1.5 (non-critical). Finviz's loosest
   upper-bound bucket is `Under 1`, which cuts into the legitimate 1.0-1.5 PASS range with no
   looser option available -- there is no bucket here that doesn't restrict, so the filter is
   gone rather than kept at a value known to be wrong.

   This is still a fast, cheap pass, not the quality judgment -- step 2 is that. Some AVOID or
   marginal names will still get through (e.g. a name at Quick Ratio 0.6 with no CFO/CL waiver
   will pass the pre-screen and then FAIL or AVOID in the real check) -- that's the accepted cost
   of not silently dropping the names that would have made it.

2. **Full check (`fundamental_check.py`, run unmodified, one subprocess per candidate).** Every
   candidate that survives Finviz gets the real sanity check + deep dive: profitability, cash
   generation, leverage, liquidity, dilution, earnings quality, Piotroski/Altman/Beneish, and the
   hard AVOID gate. This is the actual score -- Finviz only decided who gets checked. See
   `../fundamental-check/rulebook.md` for every threshold.

3. **Three files across two folders.** `results/filter_<date>.csv` (step 1's raw Finviz output,
   see above) plus `reports/good_fundamental_<date>.html` and `reports/good_fundamental_<date>.csv`
   (step 2's scored output -- the CSV is always the HTML path with its extension swapped, including
   when `--out` points somewhere else). The `results`/`reports` split mirrors what each file *is*:
   `results` is what Finviz matched, unscored; `reports` is this screener's own judgment on top.
   - **The HTML** -- a self-contained, sortable table (click any header), no external
     dependencies, works offline:
     - **Candidates** -- every non-AVOID name, ranked by Quality desc then Risk asc, with a PASS
       column for the `--min-quality`/`--max-risk` bar and each row's critical-failure list (empty
       for a clean pass).
     - **AVOID** -- candidates that tripped a critical gate, kept visible rather than dropped, so
       "why did X get excluded" has an answer in the same file.
     - **Unresolved** -- tickers Finviz returned that `fundamental_check.py` couldn't resolve or
       didn't have enough data for (exit code 2), with the reason.
     - The exact Finviz filter dict used, at the bottom, so the run is reproducible.
   - **The CSV** -- `ticker,quality,risk`, one row per candidate that got a score (AVOID names
     included, unresolved/error rows excluded since they have no score), same Quality desc / Risk
     asc ranking as the HTML's Candidates table. Plain data for spreadsheets or another script --
     no bands, no flags, no filter metadata.

## Self-contained, but not standalone

Unlike `fundamental-check` and `fetch-finviz-stocks-screener` themselves (both explicitly
self-contained, copy-anywhere skills), this screener is a thin orchestrator that calls both by
their repo paths, relative to its own folder (`../fundamental-check/fundamental_check.py`,
`../fetch-finviz-stocks-screener/run_scan.py`) as subprocesses. It adds no logic of
its own to either -- no threshold here is redefined; scoring is entirely `fundamental_check.py`'s.

## Not a screener for price/technical setups

This only judges balance sheets, cash flow and earnings quality -- the same thing
`/fundamental-check` judges for a single ticker, run market-wide. It has no opinion on entry
timing, valuation, or price action; pair its PASS list with a price-based scan (e.g.
`scanner/run_scan.py`) rather than treating a high Quality score as a buy signal by itself.

## Cost and runtime

No paid data is used -- Finviz's public screener and `fundamental_check.py`'s `yfinance` calls
are both free. Runtime is dominated by `fundamental_check.py`'s own network calls (multiple
yfinance requests per ticker, with exponential backoff on rate limits); expect roughly 10-30
seconds per candidate, parallelized across `--workers`. A default run (`--limit 150`,
`--workers 4`) takes on the order of 15-30 minutes.
