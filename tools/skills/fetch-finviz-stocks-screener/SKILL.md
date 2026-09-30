---
name: fetch-finviz-stocks-screener
description: Query Finviz's stock screener (any of its ~67 filters, 6 fixed views + a 7th custom view, and ~87 custom columns) to get a candidate ticker list matching a set of criteria. Use for an ad-hoc "find me stocks that ___" request, "run this scan and save the results to ___", or reproducing a specific screener setup described elsewhere -- any time a market-wide candidate list is needed rather than a fixed, pre-picked symbol list. Saves the resolved criteria as a reusable filter_*.json file so the same scan can be re-run later instead of re-deriving it from scratch each time.
---

# Fetch Finviz Stocks Screener

CLI + library wrapper around Finviz's screener (`https://finviz.com/screener.ashx`), returning a candidate ticker DataFrame/CSV. Self-contained: everything needed to use this skill is in this folder (`finviz_screener.py`, `presets.py`, `run_scan.py`, this file) -- it has no dependency on and no knowledge of any other file, folder, or convention outside itself. A `--filters` value can be any JSON dict of Finviz filters, and a filters file can live at any path the caller chooses; nothing here assumes a particular project layout.

## Usage

```
python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --filters "{\"Price\": \"Over $10\"}" --view technical --out out.csv
python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --view custom --columns "Ticker,RSI,Average True Range"
python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --list-filters
python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --filter-options Price
python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --list-custom-columns
```

(the `--filters` JSON examples above use bash/POSIX `\"`-escaped quoting -- adjust quoting for
other shells, e.g. PowerShell needs `""` instead of `\"`, or use `--preset`/`run_scan.py`'s
file-based `--filters <path>` instead to avoid inline-JSON quoting entirely)

- `--filters` JSON dict of `{filter name: option string}` -- any of Finviz's own filters (`--list-filters` to enumerate names, `--filter-options <name>` for that filter's valid values).
- `--preset` a named filter combo from `presets.py`, merged under `--filters` (so `--filters` can override/add individual keys on top of a preset) -- `presets.py` starts out empty (see below), so this is rarely used directly; `run_scan.py` (below) is the normal entry point and doesn't need this flag at all.
- `--view` which Finviz screener page to read -- `overview` (default), `valuation`, `ownership`, `performance`, `financial`, `technical`, or `custom` (each fixed view has its own column set; `custom` lets you pick exactly).
- `--columns` (`view=custom` only) comma-separated column names, e.g. `"Ticker,RSI,Average True Range"` -- any of Finviz's ~87 custom-screener fields (`--list-custom-columns` to enumerate).
- `--order` / `--desc` sort column and direction (`--list-filters`-adjacent: valid order names come from `finvizfinance.constants.order_dict`, generally the same names as filter/column names).
- `--signal` one of Finviz's built-in signals (e.g. `"Top Gainers"`, `"New High"`, `"Unusual Volume"`), combinable with `--filters`.
- `--ticker` restrict to a comma-separated ticker list (Finviz's own `t=` param) instead of/alongside filters.
- `--limit` stop after roughly this many rows (still fetches whole 20-row pages).
- `--out` write to this CSV path instead of printing to stdout.

As a library: `from finviz_screener import screen`, then `df = screen(filters={...}, view="technical", columns=None, limit=50)` -- same parameters as the CLI flags, returns a `pandas.DataFrame`.

## Finding the right filter/value (do this before guessing)

Whenever you have a criterion in mind and need to turn it into a real `--filters` entry, don't
guess a filter name or option string -- Finviz's own names are often not what you'd expect (e.g.
"shares" filters live under `Average Volume`/`Relative Volume`, not "Volume"; SMA filters are named
`20-Day Simple Moving Average`, not `SMA20`). Two-step lookup:

```
python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --list-filters
python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --filter-options "<filter name>"
```

(library equivalents: `list_filters()` / `filter_options(name)`.) Find the filter name first, then
look up that filter's exact valid option strings -- the value you put in `--filters`/a `filter_*.json`
file must be one of those, verbatim.

**If nothing matches**, don't force-fit an unrelated filter to approximate the criterion -- Finviz
genuinely doesn't expose every possible screening idea. Record it as unmapped/unsupported wherever
you're keeping track of the criteria, rather than silently substituting something close-enough.

## A real, discovered bug this module works around

`finvizfinance` (the underlying scraping library, both the previously-installed 1.1.0 and the latest 1.3.0) mis-parses every Ticker cell: Finviz's redesigned page renders a company-logo fallback `<span>` (just the ticker's first letter) ahead of the real ticker link, and the library's `.text` extraction concatenates both -- e.g. real ticker `ACGL` comes back as `AACGL`, `ADC` as `AADC`. Confirmed via raw HTML inspection: the row's own `href="stock?t=ACGL..."` is always correct even when the parsed text isn't. This module reuses `finvizfinance`'s filter/order/signal/column catalogue and HTTP fetch (`web_scrap`), but replaces the table parser entirely -- extracting the Ticker column from the row's own stock link instead of cell text. Verified against a live 118-row screen (including genuinely double-letter tickers like `MMM`/`RRC`, which the fix correctly leaves alone).

## Presets (`presets.py`) -- reserved for genuinely universal filter combinations

`PRESETS` here is a small, named-dict registry, but it's **usually empty**. Filter criteria for one
particular use case do NOT belong here -- they're not actually reusable outside that one use case,
so they should just be kept as a plain filters JSON file wherever makes sense for that use case (a
path passed to `run_scan.py --filters <path>`), not registered in this shared file. This file exists
only for the rare combination that's genuinely useful as a building block across many *unrelated*
callers (e.g. a generic liquidity/quality baseline), and each entry's comment must describe its own
purpose in its own terms. See `presets.py`'s own docstring for a worked (currently-unregistered)
example of the format and the bar for adding one.

## Running a scan (`run_scan.py`)

A thin runner over `screen()` for one or more filter sources at once -- either saved to a dated CSV
or printed straight to the terminal:

```
# Local filters file(s) -- point at wherever you keep them:
python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json,my-scan/filter_bearish.json --out-dir my-scan/results

# Print directly to the terminal instead -- no --out-dir. Top 20 by Relative Volume (the wrapper's
# default is descending, see --asc below), no extra flags needed for the common "give me the most
# notable matches" case:
python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --limit 20

# --limit always wants a --order alongside it -- pick the column; descending is the default, so no
# --asc needed for any of these "top 20 by ___" examples:
python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --order "Market Cap." --limit 20
python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --order "Relative Volume" --limit 20
python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --order "Performance (Year)" --limit 20

# Just the matching tickers, as one comma-separated string (agent/watchlist use):
python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --tickers-only
```

- `--filters` comma-separated **filter sources** (required) -- each token is resolved the same
  way regardless of where it comes from: checked against `presets.py` first, and if not a known
  preset name, loaded as a path to a local filters JSON file instead (any path, anywhere). One
  flag, one lookup chain -- a preset name and a file path are just two ways to name the same thing
  (a filters dict), so there's no separate "which kind of source is this" distinction to make at
  the call site.
- `--out-dir` write a `<name>_<date>.csv` per source here, **always the full scan data** --
  `--tickers-only` has no effect here (see below). **Omit `--out-dir` and results print to the
  terminal instead** (one `=== <name>: N candidates ===` block per source, then the table) -- this
  is the mode for an agent tracking live markets: run a scan, get today's matching tickers back
  directly to build a watchlist or check an alert condition, no file to go read.
- `--tickers-only` **terminal output only** -- prints just a comma-separated ticker string
  (`AAPL,MSFT,GOOGL`) instead of the full table, for an agent that just wants the match list. Doesn't
  change what gets saved when `--out-dir` is given -- a saved CSV always has the full data.
- `--view` same meaning as `finviz_screener.py`'s flag (default `performance` here, vs. `overview` there).
- `--order` same meaning as `finviz_screener.py`'s flag, but a different default (`Relative Volume`
  here vs. `Ticker` there).
- `--asc` -- **NOT the same as `finviz_screener.py`'s `--desc`.** This wrapper's default sort
  direction is **descending** (deliberately the opposite of `finviz_screener.py`'s own `ascend=True`
  default, which is left alone -- see "`--limit` truncates a sorted list, it doesn't rank" below).
  Pass `--asc` to sort ascending instead.
- `--limit` keep only the first N rows *after* sorting by `--order`/`--asc` -- matters most in
  terminal mode, to keep output bounded.

**`--limit` truncates a sorted list, it doesn't rank.** Finviz sorts the entire filtered universe
server-side by `--order` before `--limit` ever applies, so which N rows you get back depends
entirely on sort direction. `finviz_screener.py` (the underlying engine) defaults to ascending, a
neutral choice given its own default order column is `Ticker` (alphabetical either way). This
wrapper's default order column is `Relative Volume`, where ascending vs. descending is *not*
neutral -- ascending returns the matches barely above whatever threshold a filter used (e.g.
`Relative Volume: Over 1` -> results sitting at ~1.00, the least notable matches), which silently
contradicts what "give me the top N" almost always means. That's why this wrapper's own default is
descending (`--asc` to opt back into ascending) even though the underlying engine's default is
untouched -- the fix lives at the wrapper layer, not the library.

**Every saved CSV is self-describing**: a commented header block above the data rows records the
source (preset name or file path), its exact filter dict, view, order, limit, and the scan date --
plus the exact command to re-run it. A file found later doesn't need cross-referencing against
`presets.py`, its own filters file, or this script to know what produced it or how to reproduce it.
This always reflects today's market, not a fixed historical snapshot: re-running returns different
tickers each time, since the underlying screen runs against live data.

## Reuse

A generic capability, not tied to any particular project structure, workflow, or naming convention
-- call `finviz_screener.py` or `run_scan.py` from anywhere, pointing `--filters`/`--out-dir`
wherever makes sense for the caller. A caller that wants to keep scan criteria organized for later
reuse (one folder per named scan, a written explanation of what each scan is for, etc.) is free to
build that structure on top of this skill; this skill itself doesn't require or assume any of it.
