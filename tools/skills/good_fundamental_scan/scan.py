#!/usr/bin/env python3
"""
scan.py -- market-wide fundamental screener ("good_fundamental_scan").

Two stages, no LLM in either:

1. Finviz narrows the whole US market to a liquid, pre-screened candidate list
   (filter.json: tradable size/liquidity plus a coarse profitability, leverage
   and growth pass) via the fetch-finviz-stocks-screener skill, saved as
   results/filter_<date>.csv -- the same self-describing convention every
   other screener/<slug> folder in this repo uses.
2. Each candidate is run through the fundamental-check skill's full sanity +
   deep-dive gauntlet (fundamental_check.py), which is the actual quality/risk
   judge -- Finviz only limits how many slow, network-heavy checks get run.

Output is an HTML report -- every candidate's Quality score, Risk score, AVOID
flag and headline flags, ranked by quality then risk, with a PASS column for
the "good fundamentals" bar (--min-quality / --max-risk) -- plus a
ticker,quality,risk CSV of the same data alongside it.

Usage:
    python skills/good_fundamental_scan/scan.py
    python skills/good_fundamental_scan/scan.py --limit 60
    python skills/good_fundamental_scan/scan.py --full-market
    python skills/good_fundamental_scan/scan.py --tickers AAPL,MSFT,NVDA
    python skills/good_fundamental_scan/scan.py --min-quality 60 --max-risk 40
    python skills/good_fundamental_scan/scan.py --workers 4 --out reports/custom.html

Exit code is always 0 once the report is written (per-ticker failures are
recorded as rows, not fatal errors); non-zero only on a setup problem
(Finviz call failed, no candidates, etc).
"""
import argparse
import concurrent.futures
import csv
import datetime as dt
import html
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parent
FINVIZ_DIR = SKILLS_DIR / "fetch-finviz-stocks-screener"
RUN_SCAN = FINVIZ_DIR / "run_scan.py"
FUNDAMENTAL_CHECK = SKILLS_DIR / "fundamental-check" / "fundamental_check.py"
FILTER_FILE = SCRIPT_DIR / "filter.json"
REPORTS_DIR = SCRIPT_DIR / "reports"
RESULTS_DIR = SCRIPT_DIR / "results"


def get_candidates(filters_path, order, limit, view="overview"):
    """Run the Finviz pre-screen, saving results/filter_<date>.csv (the same
    self-describing convention run_scan.py's --out-dir gives every other
    screener/<slug> folder), and return (tickers, csv_path)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(RUN_SCAN), "--filters", str(filters_path),
           "--out-dir", str(RESULTS_DIR), "--view", view, "--order", order]
    if limit:
        cmd += ["--limit", str(limit)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(FINVIZ_DIR))
    if proc.returncode != 0:
        print(f"Finviz screen failed:\n{proc.stderr}", file=sys.stderr)
        sys.exit(1)
    # run_scan.py --out-dir prints "<name>: N candidates -> <path>" to stderr
    saved_line = next((ln for ln in proc.stderr.splitlines() if " -> " in ln), None)
    if not saved_line:
        print(f"Could not find saved CSV path in Finviz output:\n{proc.stderr}", file=sys.stderr)
        sys.exit(1)
    csv_path = Path(saved_line.rsplit(" -> ", 1)[1].strip())
    tickers = []
    with open(csv_path, encoding="utf-8") as f:
        rows = csv.reader(ln for ln in f if not ln.startswith("#"))
        header = next(rows, [])
        tcol = header.index("Ticker") if "Ticker" in header else 0
        for row in rows:
            if row:
                tickers.append(row[tcol])
    return tickers, csv_path


def check_one(ticker):
    """Run fundamental_check.py on one ticker; return a result dict, never raises."""
    proc = subprocess.run([sys.executable, str(FUNDAMENTAL_CHECK), ticker],
                          capture_output=True, text=True, timeout=300)
    row = {"input": ticker, "symbol": ticker, "exit_code": proc.returncode,
           "error": None, "json_path": None}
    if proc.returncode == 2:
        first_line = (proc.stderr.strip().splitlines() or ["unresolvable / insufficient data"])[0]
        row["error"] = first_line
        return row
    json_line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("JSON: ")), None)
    if not json_line:
        row["error"] = "no JSON path reported"
        return row
    jpath = Path(json_line[len("JSON: "):].strip())
    try:
        data = json.loads(jpath.read_text(encoding="utf-8"))
    except Exception as e:
        row["error"] = f"could not read report JSON ({type(e).__name__})"
        return row
    row.update({
        "symbol": data["symbol"], "name": data["name"], "sector": data["sector"],
        "industry": data["industry"], "quality": data["quality"], "risk": data["risk"],
        "quality_band": data["quality_band"], "risk_band": data["risk_band"],
        "avoid": data["avoid"], "coverage": data["coverage"],
        "critical_failures": data["critical_failures"],
        "pe": data["metrics"].get("pe"), "market_cap_usd": data["market"]["market_cap_usd"],
        "price_usd": data["market"]["price_usd"],
        "json_path": str(jpath),
    })
    try:
        row["report_text"] = jpath.with_suffix(".txt").read_text(encoding="utf-8")
    except OSError:
        row["report_text"] = None
    return row


def fmt_money(v):
    if v is None:
        return "n/a"
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"${v/div:.2f}{suf}"
    return f"${v:.0f}"


def fmt_num(v, nd=1):
    return "n/a" if v is None else f"{v:.{nd}f}"


def write_csv(rows, path):
    """ticker,quality,risk for every checked candidate, ranked Quality desc then Risk asc."""
    scored = [r for r in rows if r.get("quality") is not None]
    scored.sort(key=lambda r: (-r["quality"], r["risk"]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "quality", "risk"])
        for r in scored:
            w.writerow([r["symbol"], r["quality"], r["risk"]])


def render_html(rows, meta):
    """One self-contained, sortable HTML file -- no external CDN, works offline."""
    ranked = [r for r in rows if r.get("quality") is not None and not r["avoid"]]
    ranked.sort(key=lambda r: (-r["quality"], r["risk"]))
    avoided = [r for r in rows if r.get("quality") is not None and r["avoid"]]
    errored = [r for r in rows if r.get("quality") is None]

    def esc(s):
        return html.escape(str(s)) if s is not None else ""

    def data_row(r, i, row_id, passed=None):
        crit = "; ".join(r.get("critical_failures") or []) or "-"
        pass_cell = ""
        if passed is not None:
            pass_cell = f'<td class="{"pass" if passed else "no"}">{"PASS" if passed else "-"}</td>'
        report = r.get("report_text")
        row_attrs = f' class="data-row" data-id="{row_id}"'
        if report:
            row_attrs += f' data-report="{esc(report)}"'
        sym = esc(r["symbol"])
        return (
            f"<tr{row_attrs}>"
            f'<td>{i}</td>'
            f'<td class="sym">{sym}</td>'
            f'<td>{esc(r.get("name",""))}</td>'
            f'<td>{esc(r.get("sector",""))}</td>'
            f'<td data-sort="{r["quality"]}">{r["quality"]} ({esc(r["quality_band"])})</td>'
            f'<td data-sort="{r["risk"]}">{r["risk"]} ({esc(r["risk_band"])})</td>'
            f'<td data-sort="{r.get("pe") or -1}">{fmt_num(r.get("pe"))}</td>'
            f'<td data-sort="{r.get("market_cap_usd") or 0}">{fmt_money(r.get("market_cap_usd"))}</td>'
            f'<td data-sort="{r.get("price_usd") or 0}">{fmt_num(r.get("price_usd"),2)}</td>'
            f'<td class="crit" title="{esc(crit)}">{esc(crit)}</td>'
            f'{pass_cell}'
            "</tr>"
        )

    pass_rows = []
    for i, r in enumerate(ranked, 1):
        passed = r["quality"] >= meta["min_quality"] and r["risk"] <= meta["max_risk"]
        pass_rows.append((passed, data_row(r, i, f"r{i}", passed)))
    n_pass = sum(1 for p, _ in pass_rows if p)

    ranked_html = "\n".join(row for _, row in pass_rows)
    avoided_html = "\n".join(data_row(r, i, f"a{i}") for i, r in enumerate(avoided, 1))
    error_rows = "\n".join(
        f'<tr><td>{i}</td><td class="sym">{esc(r["input"])}</td>'
        f'<td colspan="8">{esc(r.get("error","unknown error"))}</td></tr>'
        for i, r in enumerate(errored, 1)
    )

    filters_str = json.dumps(meta["filters"], indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>good_fundamental_scan -- {meta['date']}</title>
<style>
  :root {{
    --bg: #0f1115; --panel: #171a21; --border: #2a2f3a; --text: #e6e9ef;
    --muted: #8b93a5; --good: #3ecf8e; --bad: #ef6461; --accent: #5aa9ff;
  }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, Segoe UI, Roboto, sans-serif;
         margin: 0; padding: 24px; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 28px 0 8px; color: var(--muted); }}
  .meta {{ color: var(--muted); font-size: 13px; margin-bottom: 18px; }}
  .summary {{ display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 20px; }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
           padding: 10px 16px; min-width: 120px; }}
  .card .n {{ font-size: 22px; font-weight: 600; }}
  .card .l {{ font-size: 12px; color: var(--muted); }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: var(--panel);
           border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 6px 10px; border-bottom: 1px solid var(--border); text-align: left;
            white-space: nowrap; }}
  td.crit {{ white-space: normal; max-width: 360px; color: var(--muted); font-size: 12px; }}
  th {{ cursor: pointer; user-select: none; color: var(--muted); font-weight: 600;
        position: sticky; top: 0; background: var(--panel); }}
  th:hover {{ color: var(--text); }}
  tr:hover td {{ background: #1d212b; }}
  td.sym {{ font-weight: 600; color: var(--accent); }}
  td.pass {{ color: var(--good); font-weight: 600; }}
  td.no {{ color: var(--muted); }}
  pre {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
         padding: 12px; font-size: 12px; color: var(--muted); overflow-x: auto; }}
  .scroll {{ overflow-x: auto; }}
  tr.data-row[data-report] {{ cursor: pointer; }}
  tr.detail-row td {{ background: #11141b; white-space: normal; }}
  tr.detail-row pre {{ white-space: pre-wrap; margin: 0; max-height: 70vh; }}
</style>
</head>
<body>
<h1>good_fundamental_scan</h1>
<div class="meta">
  Run {meta['date']} {meta['time']} &middot; {meta['screened']} Finviz candidates &middot;
  {meta['checked']} fundamental-checked &middot; {len(errored)} unresolved/insufficient data &middot;
  {len(avoided)} AVOID &middot; PASS bar: Quality &ge; {meta['min_quality']}, Risk &le; {meta['max_risk']}
  &middot; CSV: {esc(meta.get('csv_name',''))}
</div>

<div class="summary">
  <div class="card"><div class="n">{meta['screened']}</div><div class="l">Finviz candidates</div></div>
  <div class="card"><div class="n">{meta['checked']}</div><div class="l">Fundamentals checked</div></div>
  <div class="card"><div class="n" style="color:var(--good)">{n_pass}</div><div class="l">Pass bar</div></div>
  <div class="card"><div class="n">{len(ranked)}</div><div class="l">Not AVOID</div></div>
  <div class="card"><div class="n" style="color:var(--bad)">{len(avoided)}</div><div class="l">AVOID</div></div>
  <div class="card"><div class="n">{len(errored)}</div><div class="l">Unresolved</div></div>
</div>

<h2>Candidates -- ranked by Quality desc, Risk asc <span style="font-weight:400;color:var(--muted);font-size:12px">(click a row for its full fundamental-check report)</span></h2>
<div class="scroll">
<table id="ranked">
<thead><tr>
  <th>#</th><th>Symbol</th><th>Name</th><th>Sector</th><th>Quality</th><th>Risk</th>
  <th>P/E</th><th>Mkt Cap</th><th>Price</th><th>Critical failures</th><th>Bar</th>
</tr></thead>
<tbody>
{ranked_html}
</tbody>
</table>
</div>

<h2>AVOID -- critical gate tripped</h2>
<div class="scroll">
<table id="avoided">
<thead><tr>
  <th>#</th><th>Symbol</th><th>Name</th><th>Sector</th><th>Quality</th><th>Risk</th>
  <th>P/E</th><th>Mkt Cap</th><th>Price</th><th>Critical failures</th>
</tr></thead>
<tbody>
{avoided_html or '<tr><td colspan="10">none</td></tr>'}
</tbody>
</table>
</div>

<h2>Unresolved / insufficient data</h2>
<div class="scroll">
<table id="errors">
<thead><tr><th>#</th><th>Input</th><th colspan="8">Reason</th></tr></thead>
<tbody>
{error_rows or '<tr><td colspan="9">none</td></tr>'}
</tbody>
</table>
</div>

<h2>Finviz pre-screen filters</h2>
<pre>{esc(filters_str)}</pre>

<script>
document.querySelectorAll('table').forEach(function(table) {{
  var thead = table.querySelector('thead');
  if (!thead) return;
  thead.querySelectorAll('th').forEach(function(th, idx) {{
    var dir = 1;
    th.addEventListener('click', function() {{
      var tbody = table.querySelector('tbody');
      tbody.querySelectorAll('tr.detail-row').forEach(function(d) {{ d.remove(); }});
      var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
      rows.sort(function(a, b) {{
        var ca = a.children[idx], cb = b.children[idx];
        if (!ca || !cb) return 0;
        var va = ca.getAttribute('data-sort');
        var vb = cb.getAttribute('data-sort');
        if (va !== null && vb !== null) {{
          return (parseFloat(va) - parseFloat(vb)) * dir;
        }}
        return ca.textContent.localeCompare(cb.textContent) * dir;
      }});
      rows.forEach(function(r) {{ tbody.appendChild(r); }});
      dir *= -1;
    }});
  }});
}});

document.querySelectorAll('table').forEach(function(table) {{
  var tbody = table.querySelector('tbody');
  if (!tbody) return;
  tbody.addEventListener('click', function(e) {{
    var row = e.target.closest('tr.data-row');
    if (!row || !tbody.contains(row)) return;
    var next = row.nextElementSibling;
    if (next && next.classList.contains('detail-row') && next.dataset.for === row.dataset.id) {{
      next.remove();
      return;
    }}
    var open = tbody.querySelector('tr.detail-row');
    if (open) open.remove();
    var report = row.getAttribute('data-report');
    if (!report) return;
    var detail = document.createElement('tr');
    detail.className = 'detail-row';
    detail.dataset.for = row.dataset.id;
    var td = document.createElement('td');
    td.colSpan = row.children.length;
    var pre = document.createElement('pre');
    pre.textContent = report;
    td.appendChild(pre);
    detail.appendChild(td);
    row.after(detail);
  }});
}});
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--filters", default=str(FILTER_FILE),
                    help="Finviz filters JSON path (default: filter.json beside this script)")
    ap.add_argument("--order", default="Market Cap.",
                    help='Finviz sort column before --limit truncates (default "Market Cap.")')
    ap.add_argument("--view", default="overview",
                    choices=["overview", "valuation", "ownership", "performance", "financial",
                             "technical", "custom"],
                    help='Finviz screener view saved to results/filter_<date>.csv (default '
                         '"overview" -- company/sector/market cap/P-E, more useful here than the '
                         'other folders\' performance-percentage default)')
    ap.add_argument("--limit", type=int, default=150,
                    help="Max Finviz candidates to run fundamental_check on (default 150; each check "
                         "is a slow, network-heavy subprocess). 0 = no limit, same as --full-market.")
    ap.add_argument("--full-market", action="store_true",
                    help="Run the pre-screen filter over the entire Finviz-filtered market with no "
                         "cap (equivalent to --limit 0). A run this size can mean many hundreds of "
                         "fundamental_check subprocesses -- consider --workers and expect a long runtime.")
    ap.add_argument("--tickers", default=None,
                    help="Comma-separated ticker list -- skip Finviz and check exactly these")
    ap.add_argument("--workers", type=int, default=4,
                    help="Parallel fundamental_check subprocesses (default 4 -- yfinance rate-limits "
                         "harder under concurrent load, so higher isn't necessarily faster)")
    ap.add_argument("--min-quality", type=int, default=55,
                    help="PASS bar: minimum Quality score (default 55)")
    ap.add_argument("--max-risk", type=int, default=45,
                    help="PASS bar: maximum Risk score (default 45)")
    ap.add_argument("--out", default=None,
                    help="Output HTML path (default: reports/good_fundamental_<date>.html)")
    ap.add_argument("--candidates-out", default=None,
                    help="Write the pre-filter candidate list (one ticker per line) to this path "
                         "(default: reports/candidates_<date>.txt). Pass an empty string to skip "
                         "writing it.")
    ap.add_argument("--no-browser", action="store_true",
                    help="Don't open the finished HTML report in a browser (default: open it).")
    args = ap.parse_args()

    now = dt.datetime.now()
    today = now.date().isoformat()

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        filters_used = {"(bypassed -- explicit --tickers)": args.tickers}
    else:
        filters_path = Path(args.filters)
        filters_used = json.loads(filters_path.read_text(encoding="utf-8"))
        limit = None if args.full_market else (args.limit if args.limit > 0 else None)
        if limit is None:
            print("Pre-screen: no --limit -- scanning the entire Finviz-filtered universe.",
                  file=sys.stderr)
        else:
            print(f"Pre-screen: taking top {limit} candidates by {args.order}.",
                  file=sys.stderr)
        tickers, filter_csv_path = get_candidates(filters_path, args.order, limit, args.view)
        print(f"Pre-screen saved: {filter_csv_path}", file=sys.stderr)

    print(f"Pre-screen found {len(tickers)} candidates.", file=sys.stderr)

    if not tickers:
        print("No candidates to check (empty Finviz result or ticker list).", file=sys.stderr)
        sys.exit(1)

    if args.candidates_out != "":
        cand_path = Path(args.candidates_out) if args.candidates_out \
            else REPORTS_DIR / f"candidates_{today}.txt"
        cand_path.parent.mkdir(parents=True, exist_ok=True)
        cand_path.write_text("\n".join(tickers) + "\n", encoding="utf-8")
        print(f"Candidates written: {cand_path}", file=sys.stderr)

    print(f"Checking {len(tickers)} candidates with {args.workers} workers...", file=sys.stderr)
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(check_one, t): t for t in tickers}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            t = futures[fut]
            done += 1
            try:
                row = fut.result()
            except subprocess.TimeoutExpired:
                row = {"input": t, "symbol": t, "error": "timed out (yfinance rate-limited "
                       "under concurrent load -- retry with fewer --workers)",
                       "exit_code": -1, "json_path": None}
            except Exception as e:
                row = {"input": t, "symbol": t, "error": f"{type(e).__name__}: {e}",
                       "exit_code": -1, "json_path": None}
            rows.append(row)
            status = row.get("error") or f"quality={row.get('quality')} risk={row.get('risk')}"
            print(f"  [{done}/{len(tickers)}] {t}: {status}", file=sys.stderr)

    checked = sum(1 for r in rows if r.get("quality") is not None)
    meta = {
        "date": now.date().isoformat(), "time": now.strftime("%H:%M"),
        "screened": len(tickers), "checked": checked,
        "min_quality": args.min_quality, "max_risk": args.max_risk,
        "filters": filters_used,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else REPORTS_DIR / f"good_fundamental_{meta['date']}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = out_path.with_suffix(".csv")
    meta["csv_name"] = csv_path.name
    out_path.write_text(render_html(rows, meta), encoding="utf-8")
    print(f"Report: {out_path}", file=sys.stderr)

    write_csv(rows, csv_path)
    print(f"CSV: {csv_path}", file=sys.stderr)

    if not args.no_browser:
        os.startfile(out_path.resolve())

    print(str(out_path))


if __name__ == "__main__":
    main()
