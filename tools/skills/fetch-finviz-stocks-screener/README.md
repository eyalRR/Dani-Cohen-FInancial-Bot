# fetch-finviz-stocks-screener

Queries Finviz's stock screener (any of its filters, views, and custom columns) for a
candidate ticker list matching a set of criteria -- no LLM in the loop.

```bash
python run_scan.py --filters my-scan/filter_bullish.json --order "Market Cap." --limit 20
```

Prints the matching rows as a table to the terminal (or saves a dated CSV per filter source
with `--out-dir`); pass `--tickers-only` for just a comma-separated ticker string. See
`SKILL.md` for the full flag reference (`finviz_screener.py`'s lower-level CLI, presets,
`--view`/`--columns`, filter/option discovery, etc.) and the module's known workarounds.

## Standalone

Self-contained: everything needed is in this folder (`finviz_screener.py`, `presets.py`,
`run_scan.py`). It has no dependency on any other file, folder, or repo layout -- `--filters`
and `--out-dir` can point anywhere.

```bash
pip install finvizfinance pandas
python run_scan.py --filters '{"Price": "Over $10"}' --view technical --limit 10
```
