"""
General-purpose Finviz stock screener.

Reuses the `finvizfinance` library's filter/order/signal catalogue and its HTTP fetch (`web_scrap`),
but replaces its table parser. `finvizfinance` 1.3.0 (latest as of writing) mis-parses the Ticker
column: Finviz now renders each ticker cell with a company-logo fallback `<span>` (just the first
letter) ahead of the real ticker link, and finvizfinance's `.text` extraction concatenates both --
e.g. "ACGL" comes back as "AACGL". This module instead reads the true ticker from the row's own
stock link (`href="stock?t=ACGL..."`), which is unambiguous. Every other column is parsed exactly
as finvizfinance already does (unaffected by the bug). Verified against finvizfinance 1.1.0 and
1.3.0 -- both still exhibit the doubled-first-letter bug as of this writing.

Not tied to any one use case or filter set -- pass any combination of Finviz's own filters (see
list_filters()/filter_options()) and any of its 6 fixed screener views (Overview, Valuation,
Ownership, Performance, Financial, Technical) plus a 7th, `custom`, for picking an arbitrary column
set (see below) -- so other scans/screens can reuse this without duplicating the scraping/parsing
logic. Reusable, named filter combinations that are genuinely useful across many unrelated
scans/screens belong in presets.py (see that file's own docstring for the bar); one-off filter sets
tied to a single scan should just be passed directly, not registered anywhere in this folder.

Usage as a library:
    from finviz_screener import screen
    df = screen({"Average Volume": "Over 1M", "Price": "Over $10"})

`view="custom"` additionally accepts a `columns=` list of column names (any field Finviz's custom
screener offers, e.g. "RSI" or "Average True Range" -- see list_custom_columns()), for scans that
want an exact, arbitrary field set rather than one of the 6 fixed views' own column sets.

Usage as a CLI (see this skill's SKILL.md for the full flag reference; the --filters JSON example
below uses bash/POSIX \"-escaped quoting -- other shells (e.g. PowerShell) need different quoting):
    python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --filters "{\"Price\": \"Over $10\"}" --view technical --out out.csv
    python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --view custom --columns "Ticker,RSI,Average True Range"
    python .claude/skills/fetch-finviz-stocks-screener/finviz_screener.py --list-filters
"""

import argparse
import json
import re
import sys
import time

import pandas as pd
from finvizfinance.constants import CUSTOM_SCREENER_COLUMNS, NUMBER_COL, filter_dict, order_dict, signal_dict
from finvizfinance.util import number_covert, web_scrap

# Finviz's own custom-screener column IDs (view="custom" only), by human-readable name.
_CUSTOM_COLUMN_IDS = {name: int(cid) for cid, name in CUSTOM_SCREENER_COLUMNS.items()}

# Finviz's own `v=` page codes for each screener view -- each exposes a different column set.
VIEWS = {
    "overview": 111,
    "valuation": 121,
    "ownership": 131,
    "performance": 141,
    "custom": 151,
    "financial": 161,
    "technical": 171,
}

SCREENER_URL = "https://finviz.com/screener.ashx"
PAGE_SIZE = 20
_TICKER_HREF_RE = re.compile(r"[?&]t=([A-Za-z0-9.\-]+)")


def list_filters() -> list[str]:
    """Every filter name accepted by `filters` (Finviz's own catalogue, via finvizfinance)."""
    return list(filter_dict.keys())


def filter_options(name: str) -> list[str]:
    """Valid option strings for a given filter name, e.g. filter_options("Price")."""
    if name not in filter_dict:
        raise ValueError(f"Unknown filter {name!r}. See list_filters().")
    return list(filter_dict[name]["option"].keys())


def list_orders() -> list[str]:
    return list(order_dict.keys())


def list_signals() -> list[str]:
    return list(signal_dict.keys())


def list_custom_columns() -> list[str]:
    """Column names selectable via `columns=` when view="custom" (Finviz's own custom-column set)."""
    return list(_CUSTOM_COLUMN_IDS.keys())


def _build_params(
    filters: dict, view: str, order: str, ascend: bool, signal: str, ticker: str, columns: list | None
) -> dict:
    if view not in VIEWS:
        raise ValueError(f"Unknown view {view!r}. Choices: {list(VIEWS)}")
    if order not in order_dict:
        raise ValueError(f"Unknown order {order!r}. See list_orders().")
    if columns and view != "custom":
        raise ValueError("`columns` is only used with view='custom'")

    params: dict = {"v": VIEWS[view]}

    if columns:
        ids = []
        for name in columns:
            if name not in _CUSTOM_COLUMN_IDS:
                raise ValueError(f"Unknown custom column {name!r}. See list_custom_columns().")
            cid = _CUSTOM_COLUMN_IDS[name]
            if cid not in ids:
                ids.append(cid)
        if 0 in ids:
            ids.remove(0)
        ids.insert(0, 0)  # Finviz always includes the "No." rank column first
        params["c"] = ",".join(str(i) for i in ids)

    if signal:
        if signal not in signal_dict:
            raise ValueError(f"Unknown signal {signal!r}. See list_signals().")
        params["s"] = signal_dict[signal]

    if ticker:
        params["t"] = ticker

    codes = []
    for key, value in filters.items():
        if key not in filter_dict:
            raise ValueError(f"Unknown filter {key!r}. See list_filters().")
        options = filter_dict[key]["option"]
        if value not in options:
            raise ValueError(f"Unknown option {value!r} for filter {key!r}. Choices: {list(options)}")
        code = options[value]
        if code:
            codes.append(f"{filter_dict[key]['prefix']}_{code}")
    if codes:
        params["f"] = ",".join(codes)

    params["o"] = ("" if ascend else "-") + order_dict[order]
    return params


def _row_ticker(cell) -> str:
    """The true ticker from the cell's own stock link, bypassing finvizfinance's buggy `.text`
    concatenation of the company-logo fallback letter + the real ticker (see module docstring)."""
    for a in cell.find_all("a", href=True):
        m = _TICKER_HREF_RE.search(a["href"])
        if m:
            return m.group(1)
    return cell.get_text(strip=True)


def _table_headers(soup) -> list[str]:
    table = soup.find("table", class_="screener_table")
    header_row = table.find_all("tr")[0]
    return [th.get_text(strip=True) for th in header_row.find_all("th")][1:]  # drop rank column


def _parse_page(soup, headers: list[str]) -> list[dict]:
    table = soup.find("table", class_="screener_table")
    if table is None:
        return []
    rows = table.find_all("tr")[1:]  # skip header row
    num_cols = {h for h in headers if h in NUMBER_COL}

    out = []
    for row in rows:
        cells = row.find_all("td")[1:]  # skip the rank column
        if len(cells) != len(headers):
            continue
        record = {}
        for header, cell in zip(headers, cells):
            if header == "Ticker":
                record[header] = _row_ticker(cell)
            elif header in num_cols:
                record[header] = number_covert(cell.get_text(strip=True))
            else:
                record[header] = cell.get_text(strip=True)
        out.append(record)
    return out


def _page_count(soup) -> int:
    select = soup.find(id="pageSelect")
    if select is None:
        return 1 if soup.find("table", class_="screener_table") else 0
    return len(select.find_all("option"))


def screen(
    filters: dict | None = None,
    view: str = "overview",
    order: str = "Ticker",
    ascend: bool = True,
    signal: str = "",
    ticker: str = "",
    columns: list | None = None,
    limit: int | None = None,
    sleep_sec: float = 1.0,
    verbose: bool = False,
) -> pd.DataFrame:
    """Run a Finviz screener query and return the results as a DataFrame.

    filters: {filter name -> option string}, e.g. {"Price": "Over $10", "Average Volume": "Over 1M"}.
             See list_filters()/filter_options() for valid names/values.
    view: which Finviz screener page to read -- each exposes a different column set (see VIEWS).
    signal: one of list_signals() (e.g. "Top Gainers", "New High"), combinable with filters.
    ticker: comma-separated ticker list to restrict the screen to (Finviz's own `t=` param).
    columns: view="custom" only -- exact list of column names to return (see list_custom_columns()).
    limit: stop after roughly this many rows (still fetches whole pages of 20, so may return a
           few extra past the exact limit).
    """
    filters = filters or {}
    params = _build_params(filters, view, order, ascend, signal, ticker, columns)

    soup = web_scrap(SCREENER_URL, params)
    pages = _page_count(soup)
    if pages == 0:
        return pd.DataFrame()

    headers = _table_headers(soup)
    records = _parse_page(soup, headers)

    page = 1
    while page < pages and (limit is None or len(records) < limit):
        time.sleep(sleep_sec)
        if verbose:
            print(f"[finviz_screener] page {page + 1}/{pages}", file=sys.stderr)
        params["r"] = page * PAGE_SIZE + 1
        soup = web_scrap(SCREENER_URL, params)
        records.extend(_parse_page(soup, headers))
        page += 1

    df = pd.DataFrame(records, columns=headers)
    if limit is not None:
        df = df.head(limit)
    return df


def _cli():
    parser = argparse.ArgumentParser(description="General-purpose Finviz screener.")
    parser.add_argument("--filters", help='JSON dict of {filter name: option}, e.g. \'{"Price": "Over $10"}\'')
    parser.add_argument(
        "--preset",
        help="Name of a preset from this folder's presets.py "
        "(.claude/skills/fetch-finviz-stocks-screener/presets.py, usually empty -- merged under --filters)",
    )
    parser.add_argument("--view", default="overview", choices=list(VIEWS))
    parser.add_argument("--order", default="Ticker")
    parser.add_argument("--desc", action="store_true", help="Sort descending instead of ascending")
    parser.add_argument("--signal", default="")
    parser.add_argument("--ticker", default="", help="Comma-separated ticker filter, e.g. AAPL,MSFT")
    parser.add_argument("--columns", help='view="custom" only -- comma-separated column names, e.g. "Ticker,RSI"')
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", help="Write results to this CSV path instead of printing")
    parser.add_argument("--list-filters", action="store_true", help="Print all filter names and exit")
    parser.add_argument("--filter-options", help="Print valid options for one filter name and exit")
    parser.add_argument("--list-custom-columns", action="store_true", help="Print all view=custom column names and exit")
    args = parser.parse_args()

    if args.list_filters:
        for name in list_filters():
            print(name)
        return

    if args.filter_options:
        for opt in filter_options(args.filter_options):
            print(opt)
        return

    if args.list_custom_columns:
        for name in list_custom_columns():
            print(name)
        return

    filters: dict = {}
    if args.preset:
        from presets import PRESETS

        if args.preset not in PRESETS:
            parser.error(f"Unknown preset {args.preset!r}. Choices: {list(PRESETS)}")
        filters.update(PRESETS[args.preset])
    if args.filters:
        filters.update(json.loads(args.filters))

    columns = [c.strip() for c in args.columns.split(",")] if args.columns else None

    df = screen(
        filters=filters,
        view=args.view,
        order=args.order,
        ascend=not args.desc,
        signal=args.signal,
        ticker=args.ticker,
        columns=columns,
        limit=args.limit,
        verbose=True,
    )

    if args.out:
        df.to_csv(args.out, index=False)
        print(f"Wrote {len(df)} rows to {args.out}", file=sys.stderr)
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    _cli()
