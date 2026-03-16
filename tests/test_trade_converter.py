# test_trade_converter.py
"""
Standalone tests for TradeConverter.
Run from the financial_bot directory:
    python test_trade_converter.py

Requires internet access to fetch live prices via yfinance.
"""

import sys
import os

# Add tools directory to path (parent directory of tests)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from trade_converter import TradeConverter, ConvertedTrade, TradeLevel


def sep(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


# ===========================================================================
# Test 1 – Long NDX trade  →  auto-selects TQQQ
# ===========================================================================
sep("Test 1 | Long NDX -> auto-selects TQQQ")

converter = TradeConverter('NDX')
print(f"  {converter!r}")

f0 = converter.F0
result: ConvertedTrade = converter.convert_trade(
    entry=round(f0),
    stop=round(f0 * 0.986),
    targets=[round(f0 * 1.014), round(f0 * 1.028)],
)
assert result.etf_symbol == 'TQQQ'
assert result.trade_direction == 'long'
print(result.summary_text)
print(f"\n✔  ETF auto-selected: {result.etf_symbol}")


# ===========================================================================
# Test 2 – Short NDX trade on the SAME converter  →  auto-selects SQQQ
# ===========================================================================
sep("Test 2 | Short NDX (same converter) -> auto-selects SQQQ")

result2: ConvertedTrade = converter.convert_trade(
    entry=round(f0),
    stop=round(f0 * 1.014),        # stop ABOVE entry for a short
    targets=[round(f0 * 0.986), round(f0 * 0.972)],
)
assert result2.etf_symbol == 'SQQQ'
assert result2.trade_direction == 'short'
print(result2.summary_text)

entry_lvl, target_lvl = result2.levels[0], result2.levels[2]
assert target_lvl.etf_price > entry_lvl.etf_price, (
    "SQQQ should rise when NDX falls"
)
print(f"\n✔  SQQQ rises as NDX falls: {entry_lvl.etf_price:.2f} -> {target_lvl.etf_price:.2f}")


# ===========================================================================
# Test 3 – SPX long  →  auto-selects SPXL
# ===========================================================================
sep("Test 3 | Long SPX -> auto-selects SPXL")

conv_spx = TradeConverter('SPX')
f0_spx = conv_spx.F0
result3 = conv_spx.convert_trade(
    entry=round(f0_spx),
    stop=round(f0_spx * 0.986),
    targets=[round(f0_spx * 1.014)],
)
assert result3.etf_symbol == 'SPXL'
print(result3.summary_text)


# ===========================================================================
# Test 4 – ES futures label  →  same mapping as SPX
# ===========================================================================
sep("Test 4 | ES futures label -> same ETF mapping as SPX")

conv_es = TradeConverter('ES')
f0_es = conv_es.F0
result4 = conv_es.convert_trade(
    entry=round(f0_es),
    stop=round(f0_es * 0.986),
    targets=[round(f0_es * 1.014)],
)
assert result4.etf_symbol == 'SPXL'
print(result4.summary_text)
print(f"\n✔  ES resolved to {result4.etf_symbol}")


# ===========================================================================
# Test 5 – Leverage override
# ===========================================================================
sep("Test 5 | Leverage override (1x instead of default 3x)")

conv_1x = TradeConverter('NDX', leverage=1)
result5 = conv_1x.convert_trade(
    entry=round(conv_1x.F0),
    stop=round(conv_1x.F0 * 0.986),
    targets=[round(conv_1x.F0 * 1.014)],
)
assert result5.leverage == 1.0
print(result5.summary_text)
print(f"\n✔  Leverage used: {result5.leverage}x")


# ===========================================================================
# Test 6 – format_summary() at different precision
# ===========================================================================
sep("Test 6 | Re-format result with 4 decimal places")
print(converter.format_summary(result, decimals=4))


# ===========================================================================
# Test 7 – Error handling
# ===========================================================================
sep("Test 7 | Error handling")

try:
    TradeConverter('UNKNOWN')
except ValueError as e:
    print(f"✔  Unknown underlying: {e}")

try:
    converter.convert_trade(entry=21500, stop=21200, targets=[])
except ValueError as e:
    print(f"✔  Empty targets rejected: {e}")


# ===========================================================================
# Test 8 – fetch_info in result
# ===========================================================================
sep("Test 8 | fetch_info in ConvertedTrade")
print(f"  fetch_info: {result.fetch_info}")
assert result.fetch_info['etf_symbol'] == 'TQQQ'
assert result.fetch_info['F0'] == converter.F0
print("✔  fetch_info populated correctly")


# ===========================================================================
# Test 9 – Class helpers
# ===========================================================================
sep("Test 9 | Class-level helpers")
print(f"  get_supported_underlyings(): {TradeConverter.get_supported_underlyings()}")
print(f"  get_supported_etfs()       : {TradeConverter.get_supported_etfs()}")
print(f"  get_etf_for_underlying(NDX): {TradeConverter.get_etf_for_underlying('NDX')}")


print(f"\n{'='*60}\n  All tests completed.\n{'='*60}\n")
