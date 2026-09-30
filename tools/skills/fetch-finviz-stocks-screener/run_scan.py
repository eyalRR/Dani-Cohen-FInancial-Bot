"""
Generic point-in-time candidate scan runner: given one or more filter sources (`--filters`), runs
each through `screen()` and either saves a dated CSV per source (`--out-dir`) or prints the result
straight to the terminal (no `--out-dir`).

Each `--filters` token is resolved the same way regardless of where it comes from -- checked
against this skill's `presets.py` first (a small, usually-empty dict of genuinely universal filter
combinations reusable across unrelated callers), and if not found there, loaded as a path to a
local filters JSON file instead (the normal case -- criteria for one particular use case should
just be kept as a file wherever makes sense for that use case, not registered centrally). One flag,
one lookup chain -- no separate "which kind of source is this" distinction to make at the call site.

The no-`--out-dir` / terminal mode is meant for live use: an agent watching the market for tickers
matching some filter criteria (a watchlist, an alert condition) wants the current match list back
directly, not a file to go read -- `--limit` keeps that output bounded, `--tickers-only` reduces it
to just a comma-separated ticker string. `--tickers-only` only changes what's printed to the
terminal; a saved CSV (`--out-dir`) always has the full scan data regardless.

**`--limit` truncates whatever order the results are already sorted into -- it does not pick "the
best N" by itself.** `screen()` (the underlying `finviz_screener.py` engine, whose own default sort
direction is intentionally left alone here) sorts the *entire* filtered universe server-side by
`--order`, then `--limit` just keeps the first N rows of that already-sorted list. This wrapper's
own default is **descending** (`ascend=False` unless `--asc` is passed) specifically so that a
naive `--limit N` with no other flags returns the N *highest* values of `--order` (default
"Relative Volume" -- the most actively-traded matches) rather than silently returning the N
*lowest* ones sitting just above whatever filter threshold was used. Pass `--asc` to flip it back.

Every saved CSV is self-describing: a commented header block (source, filters, view, order, limit,
scan date, and the exact command to re-run it) above the data rows, so a file found later can be
understood and reproduced without cross-referencing this script, `presets.py`, or a scan's own
filters file by hand. This always reflects today's market, not a fixed historical snapshot:
re-running returns different tickers each time, since the underlying screen runs against live data.

Usage:
    # Local filters file(s) -- point at wherever the caller keeps them:
    python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json,my-scan/filter_bearish.json --out-dir my-scan/results

    # A universal preset name from presets.py (rare):
    python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters some_universal_preset --out-dir some-scan/results

    # Print straight to the terminal instead (typical agent use) -- no --out-dir, every matching
    # row (still sorted by the default --order, just not truncated since --limit is omitted):
    python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json

    # --limit always wants a --order alongside it -- pick the column, descending is the default
    # (see above), so no --asc needed for any of these "top 20 by ___" examples:
    python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --order "Market Cap." --limit 20
    python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --order "Relative Volume" --limit 20
    python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --order "Performance (Year)" --limit 20

    # Just the matching tickers, as one comma-separated string (agent/watchlist use):
    python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters my-scan/filter_bullish.json --tickers-only
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

from finviz_screener import screen
from presets import PRESETS


def resolve_filter_source(token: str) -> tuple[str, dict, str]:
    """Returns (name, filters_dict, recreate_token) -- token is a preset name (checked first) or a
    path to a local filters JSON file (fallback). Raises ValueError if neither resolves."""
    if token in PRESETS:
        return token, PRESETS[token], token

    path = Path(token)
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            return path.stem, json.load(f), path.as_posix()

    raise ValueError(f"{token!r} is neither a known preset ({list(PRESETS)}) nor an existing filters file")


def _criteria_header(recreate_token: str, filters: dict, view: str, order: str, ascend: bool, limit: int | None) -> str:
    """Commented header block so a saved CSV can be understood and re-run without cross-referencing
    presets.py, a scan's own filters file, or this script by hand -- the exact criteria that
    produced it, in the file itself."""
    recreate = (
        f"python .claude/skills/fetch-finviz-stocks-screener/run_scan.py --filters {recreate_token} "
        f'--view {view} --order "{order}"' + (" --asc" if ascend else "") + (f" --limit {limit}" if limit else "")
    )
    lines = [
        f"# source: {recreate_token}",
        f"# filters: {json.dumps(filters)}",
        f"# view: {view}",
        f"# order: {order} ({'ascending' if ascend else 'descending'})",
        f"# limit: {limit if limit is not None else 'none'}",
        f"# scanned: {date.today().isoformat()}",
        f"# recreate: {recreate}",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--filters",
        required=True,
        help="Comma-separated filter sources -- each is a preset name from presets.py, or a path to a local filters JSON file",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory to write dated, self-describing CSVs into (created if missing). Omit to print results to the terminal instead.",
    )
    parser.add_argument("--view", default="performance", choices=["overview", "valuation", "ownership", "performance", "financial", "technical", "custom"])
    parser.add_argument("--order", default="Relative Volume", help='Sort column (default "Relative Volume") -- combines with --limit, see module docstring')
    parser.add_argument(
        "--asc",
        action="store_true",
        help="Sort ascending instead of descending. Default is descending (highest --order value first) so a plain --limit N returns the top N, not the bottom N.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Keep only the first N rows after sorting by --order/--asc (applies whether writing CSVs or printing)")
    parser.add_argument(
        "--tickers-only",
        action="store_true",
        help='Terminal output only ("AAPL,MSFT,GOOGL") instead of the full table -- has no effect on --out-dir, which always saves full data',
    )
    args = parser.parse_args()

    try:
        jobs = [resolve_filter_source(t.strip()) for t in args.filters.split(",")]
    except ValueError as e:
        parser.error(str(e))

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    ascend = args.asc

    for i, (name, filters, recreate_token) in enumerate(jobs):
        if i > 0:
            time.sleep(2.0)  # same pacing screen() already uses between its own paginated fetches
        df = screen(filters, view=args.view, order=args.order, ascend=ascend, limit=args.limit, verbose=True)

        if out_dir:
            stamp = date.today().isoformat()
            out_path = out_dir / f"{name}_{stamp}.csv"
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                f.write(_criteria_header(recreate_token, filters, args.view, args.order, ascend, args.limit))
                df.to_csv(f, index=False)
            print(f"{name}: {len(df)} candidates -> {out_path}", file=sys.stderr)
        elif args.tickers_only:
            prefix = f"{name}: " if len(jobs) > 1 else ""
            print(f"{prefix}{','.join(df['Ticker'].tolist())}")
        else:
            header = f"=== {name}: {len(df)} candidates ===" if len(jobs) > 1 else f"{name}: {len(df)} candidates"
            print(header)
            print(df.to_string(index=False) if len(df) else "(no matches)")
            print()


if __name__ == "__main__":
    main()
