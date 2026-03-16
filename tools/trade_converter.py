# trade_converter.py
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeLevel:
    label: str
    underlying_price: float
    underlying_pct_change: float
    etf_price: float
    etf_pct_change: float


@dataclass
class ConvertedTrade:
    underlying_symbol: str
    etf_symbol: str
    leverage: float
    etf_direction: int
    trade_direction: str        # 'long' or 'short'
    levels: list = field(default_factory=list)
    summary_text: str = ""
    fetch_info: dict = field(default_factory=dict)


class TradeConverter:
    """
    Converts a Dani Cohen trade plan (entry / stop / targets on the underlying)
    to leveraged-ETF prices.

    Prices are fetched automatically from yfinance on construction.

    Supported underlyings and their ETFs:
        NDX, NQ, QQQ  →  TQQQ (long, 3×) / SQQQ (short, 3×)
        SPX, ES, SP500 →  SPXL (long, 3×) / SPXS (short, 3×)

    Direction is auto-detected per trade:
        entry < target  →  long  →  TQQQ / SPXL
        entry > target  →  short →  SQQQ / SPXS

    Formula (mirrors the HTML calculator):
        delta_pct      = (target / F0) - 1
        etf_change_pct = delta_pct * etf_direction * leverage
        predicted_etf  = E0 * (1 + etf_change_pct)

    Usage:
        converter = TradeConverter('NDX')
        result = converter.convert_trade(
            entry=21500, stop=21200, targets=[21800, 22100]
        )
        print(result.summary_text)
    """

    UNDERLYING_TO_ETFS = {
        'NDX': ('TQQQ','SQQQ'), 'NQ': ('TQQQ','SQQQ'), 'QQQ': ('TQQQ','SQQQ'),
        'SPX': ('SPXL','SPXS'), 'ES': ('SPXL','SPXS'),
        'SP500': ('SPXL','SPXS'), 'SP': ('SPXL','SPXS'),
    }
    UNDERLYING_TO_YFTICKER = {
        'NDX': '^NDX',  'NQ': 'NQ=F',   'QQQ': 'QQQ',
        'SPX': '^GSPC', 'ES': 'ES=F',   'SP500': '^GSPC', 'SP': '^GSPC',
    }
    ETF_REGISTRY = {
        'TQQQ': {'direction':  1, 'leverage': 3},
        'SQQQ': {'direction': -1, 'leverage': 3},
        'SPXL': {'direction':  1, 'leverage': 3},
        'SPXS': {'direction': -1, 'leverage': 3},
    }

    # ── Construction (fetches live prices) ──────────────────────────────────

    def __init__(self, underlying: str, leverage: Optional[float] = None) -> None:
        """
        Args:
            underlying: Futures / index label ('NDX', 'NQ', 'SPX', 'ES', …).
            leverage  : Override default 3× leverage if needed.
        """
        key = underlying.upper().strip()
        if key not in self.UNDERLYING_TO_ETFS:
            raise ValueError(f"Unknown underlying '{underlying}'. Supported: {list(self.UNDERLYING_TO_ETFS)}")

        self.underlying_symbol = key
        self._leverage_override = float(leverage) if leverage is not None else None
        self._long_etf_symbol, self._short_etf_symbol = self.UNDERLYING_TO_ETFS[key]

        # Fetch live prices
        self.F0, self._long_etf_price, self._short_etf_price = self._fetch_prices(key)
        logger.info(f"Prices loaded → {key}={self.F0:.2f}, "
                    f"{self._long_etf_symbol}={self._long_etf_price:.2f}, "
                    f"{self._short_etf_symbol}={self._short_etf_price:.2f}")

    # ── Price fetching ───────────────────────────────────────────────────────

    def _fetch_prices(self, key: str) -> tuple:
        """Fetch F0, long ETF price and short ETF price from yfinance."""
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("yfinance is required. Run: pip install yfinance") from exc

        yf_ticker = self.UNDERLYING_TO_YFTICKER[key]
        long_etf, short_etf = self.UNDERLYING_TO_ETFS[key]

        def fetch(symbol: str) -> float:
            t = yf.Ticker(symbol)
            try:
                p = t.fast_info.get('last_price') or t.fast_info.get('lastPrice')
                if p and p > 0:
                    return float(p)
            except Exception:
                pass
            hist = t.history(period='5d')
            if hist.empty:
                raise RuntimeError(f"No price data returned for '{symbol}'.")
            return float(hist['Close'].dropna().iloc[-1])

        return fetch(yf_ticker), fetch(long_etf), fetch(short_etf)

    # ── Core conversion ──────────────────────────────────────────────────────

    def convert_trade(self, entry: float, stop: float,
                      targets: list, decimals: int = 2) -> ConvertedTrade:
        """
        Convert a trade plan to ETF prices. Direction is auto-detected.

        Args:
            entry    : Entry price on the underlying.
            stop     : Stop-loss price on the underlying.
            targets  : List of target prices (at least one required).
            decimals : Decimal places for summary_text output.
        """
        if not targets:
            raise ValueError("At least one target price is required.")

        direction = "long" if targets[0] >= entry else "short"
        etf_sym, E0, etf_dir, lev = self._select_etf(direction)

        def cvt(label, price):
            d = (price / self.F0) - 1.0
            ec = d * etf_dir * lev
            return TradeLevel(label, price, d * 100, E0 * (1 + ec), ec * 100)

        levels = [cvt("Entry", entry), cvt("Stop", stop)]
        levels += [cvt(f"Target {i}", t) for i, t in enumerate(targets, 1)]

        summary = self._build_summary(etf_sym, lev, direction, levels, decimals)
        fetch_info = {
            'underlying_ticker': self.UNDERLYING_TO_YFTICKER[self.underlying_symbol],
            'F0': self.F0, 'etf_symbol': etf_sym, 'E0': E0,
        }
        return ConvertedTrade(self.underlying_symbol, etf_sym, lev, etf_dir,
                              direction, levels, summary, fetch_info)

    def format_summary(self, converted_trade: ConvertedTrade, decimals: int = 2) -> str:
        """Re-generate summary text with a different decimal precision."""
        return self._build_summary(converted_trade.etf_symbol, converted_trade.leverage,
                                   converted_trade.trade_direction, converted_trade.levels, decimals)

    # ── Class-level helpers ──────────────────────────────────────────────────

    @classmethod
    def get_supported_underlyings(cls): return list(cls.UNDERLYING_TO_ETFS)

    @classmethod
    def get_supported_etfs(cls): return list(cls.ETF_REGISTRY)

    @classmethod
    def get_etf_for_underlying(cls, underlying: str) -> dict:
        key = underlying.upper().strip()
        if key not in cls.UNDERLYING_TO_ETFS:
            raise ValueError(f"Unknown underlying '{underlying}'.")
        l, s = cls.UNDERLYING_TO_ETFS[key]
        return {'long': l, 'short': s}

    # ── Private helpers ──────────────────────────────────────────────────────

    def _select_etf(self, direction: str) -> tuple:
        sym = self._long_etf_symbol if direction == "long" else self._short_etf_symbol
        price = self._long_etf_price if direction == "long" else self._short_etf_price
        info = self.ETF_REGISTRY[sym]
        lev = self._leverage_override if self._leverage_override is not None else float(info['leverage'])
        return sym, price, info['direction'], lev

    def _build_summary(self, etf_sym, leverage, direction, levels, decimals) -> str:
        emoji = "📈" if direction == "long" else "📉"
        lbl   = "Long (bullish)" if direction == "long" else "Short (bearish)"
        fmt   = f".{decimals}f"
        lines = [
            f"{etf_sym} Targets | {self.underlying_symbol} trade (leverage {leverage:.0f}x)",
            f"Trade direction: {lbl} {emoji}",
        ]
        for lvl in levels:
            sign = "+" if lvl.etf_pct_change >= 0 else ""
            lines.append(f"{lvl.label:<10}: underlying {lvl.underlying_price:{fmt}}"
                         f" -> {etf_sym} {lvl.etf_price:{fmt}}"
                         f"  ({sign}{lvl.etf_pct_change:.2f}%)")
        return "\n".join(lines)

    def __repr__(self):
        return (f"TradeConverter({self.underlying_symbol}, F0={self.F0:.2f}, "
                f"{self._long_etf_symbol}={self._long_etf_price:.2f}, "
                f"{self._short_etf_symbol}={self._short_etf_price:.2f})")
