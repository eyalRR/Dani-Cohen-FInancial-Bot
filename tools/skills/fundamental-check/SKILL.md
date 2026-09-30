---
name: fundamental-check
description: Run a deterministic fundamental sanity check on a single US or Tel Aviv traded stock before opening a position -- profitability, cash generation, leverage, liquidity, dilution and earnings quality -- producing green flags, red flags, a Quality score, a Risk score and a hard AVOID banner when a critical gate trips. Use when asked whether a company's fundamentals are sound, whether it has cash-flow or debt problems, whether a stock is safe to buy on fundamentals, or to vet a ticker that a price-based scan just flagged. Accepts a US ticker (AAPL), a TASE ticker (ESLT.TA), or a TASE security number (1081124). Not a valuation or price-target tool and not a screener -- it judges one company at a time.
---

# Fundamental Check

A pre-trade sanity gate. The strategy pipeline in this repo is entirely price-driven, so a scan can fire an entry on a company that is burning cash, drowning in debt or diluting every quarter. This skill is the check that catches that.

Runs with no LLM in the loop: one deterministic Python script, one argument, no flags.

## Usage

```bash
python .claude/skills/fundamental-check/fundamental_check.py AAPL
```

```bash
python .claude/skills/fundamental-check/fundamental_check.py ESLT.TA
```

```bash
python .claude/skills/fundamental-check/fundamental_check.py 1081124
```

The argument is a US ticker, a TASE ticker, or a TASE security number (the number in a Bizportal or Globes URL). Nothing else is accepted -- there are no options.

**Exit codes:** `0` clean, `1` AVOID tripped, `2` unresolvable ticker or insufficient data.

A markdown report prints to stdout. A full JSON -- every metric, threshold, verdict, resolved statement alias and diagnostics -- is written to `reports/<SYMBOL>_<DATE>.json` beside the script, and its path is the last line of output. It lists every check that ran and, separately under `skipped_checks`, every check the code defines that did not, each with the reason (the rulebook it does not apply to, or the AVOID short-circuit). It also records when the data was fetched (`fetched_at`, with a UTC offset) and the reason behind the liquidity waiver (`liquidity_waiver_note`).

## What it produces

- **Quality 0-100** -- profitability, cash generation, growth, capital allocation.
- **Risk 0-100**, higher is more dangerous -- leverage, liquidity, earnings quality.
- **AVOID banner** when any critical gate trips (negative equity, equity eroding toward zero, interest coverage below 1.5x, net debt beyond the leverage ceiling with no coverage to service it, time to live under 12 months, negative operating cash flow, dividend paid out of losses or an unfunded high-yield payout, dilution over 20% YoY, or failing tradability). Altman Z-score and Beneish M-score are scored leverage/earnings-quality checks, not AVOID-tier gates on their own.

The two scores are deliberately separate: a high-growth company with a broken balance sheet should not average out to "fine".

## Reading the output

Every flag carries the observed number and the threshold it was judged against. A `WATCH` line is a metric that failed a raw threshold but was waived for a stated reason -- read the reason, it is the interesting part. `NOT APPLICABLE` means the check does not apply to this company's rulebook, not that the company failed it.

When the Sanity Check already trips AVOID, the Deep Dive is skipped and no forensic requests are issued. The report says so, and the Risk score is then based on Sanity Check inputs only.

See [rulebook.md](rulebook.md) for every threshold and why it is set where it is.

## Self-contained

This folder imports nothing from this repo and knows nothing about its conventions. Copy it anywhere with `yfinance` and `pandas` installed and it works unchanged.
