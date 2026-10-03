"""Simulated mid prices: 5-minute geometric Brownian motion per symbol.

All timestamps are int64 microseconds since the Unix epoch (UTC).
"""

from __future__ import annotations

import numpy as np

from .reference import HKD_PEG, USD_PER_CCY, symbols_df

US_PER_MIN = 60 * 1_000_000
STEP_US = 5 * US_PER_MIN
YEAR_US = 365 * 24 * 60 * US_PER_MIN


class PriceModel:
    def __init__(self, start_us: int, end_us: int, seed: int):
        self.symbols = symbols_df().set_index("symbol")
        self.grid = np.arange(start_us, end_us + STEP_US, STEP_US, dtype=np.int64)
        rng = np.random.default_rng(seed + 11)
        dt = STEP_US / YEAR_US
        self.paths: dict[str, np.ndarray] = {}
        for sym, row in self.symbols.iterrows():
            shocks = rng.normal(0.0, row["annual_vol"] * np.sqrt(dt), size=len(self.grid))
            shocks[0] = 0.0
            self.paths[sym] = row["start_price"] * np.exp(np.cumsum(shocks))

    def price_at(self, symbol: str, ts_us: np.ndarray) -> np.ndarray:
        return np.interp(ts_us.astype(np.float64), self.grid.astype(np.float64), self.paths[symbol])

    def prices_at(self, symbols: np.ndarray, ts_us: np.ndarray) -> np.ndarray:
        out = np.empty(len(symbols), dtype=np.float64)
        for sym in np.unique(symbols):
            m = symbols == sym
            out[m] = self.price_at(sym, ts_us[m])
        return out

    def usd_per_quote(self, quote_ccys: np.ndarray, ts_us: np.ndarray) -> np.ndarray:
        """USD value of one unit of each quote currency at each timestamp (MT5 'RateProfit')."""
        out = np.ones(len(quote_ccys), dtype=np.float64)
        for ccy in np.unique(quote_ccys):
            m = quote_ccys == ccy
            if ccy == "USD":
                continue
            if ccy == "HKD":
                out[m] = 1.0 / HKD_PEG
                continue
            pair, invert = USD_PER_CCY[ccy]
            px = self.price_at(pair, ts_us[m])
            out[m] = 1.0 / px if invert else px
        return out

    def rescale_to(self, prices: dict[str, float], at_us: int) -> "PriceModel":
        """Scale every path so its price at ``at_us`` equals ``prices`` (keeps servers consistent)."""
        for sym, path in self.paths.items():
            self.paths[sym] = path * (prices[sym] / float(self.price_at(sym, np.array([at_us]))[0]))
        return self

    def last_prices(self) -> dict[str, float]:
        return {sym: float(path[-1]) for sym, path in self.paths.items()}


class LivePrices:
    """Random-walk prices for the drip producer, continuing from the saved state."""

    def __init__(self, last: dict[str, float], seed: int):
        self.symbols = symbols_df().set_index("symbol")
        self.px = dict(last)
        self.rng = np.random.default_rng(seed)

    def step(self, seconds: float) -> None:
        dt = seconds / (365 * 24 * 3600)
        for sym, row in self.symbols.iterrows():
            self.px[sym] *= float(np.exp(self.rng.normal(0.0, row["annual_vol"] * np.sqrt(dt) * 3.0)))

    def price(self, symbol: str) -> float:
        return self.px[symbol]

    def usd_per_quote(self, ccy: str) -> float:
        if ccy == "USD":
            return 1.0
        if ccy == "HKD":
            return 1.0 / HKD_PEG
        pair, invert = USD_PER_CCY[ccy]
        return 1.0 / self.px[pair] if invert else self.px[pair]
