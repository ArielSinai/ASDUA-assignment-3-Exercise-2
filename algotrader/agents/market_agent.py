from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class MarketSignal:
    symbol: str
    action: str   # "BUY" | "SELL" | "HOLD"
    confidence: float
    reason: str


class MarketAgent:
    """
    Minimal MA crossover agent (matches the unit tests):
    - BUY  when SMA(short) > SMA(long) by threshold
    - SELL when SMA(short) < SMA(long) by threshold
    - HOLD if not enough data
    """

    def __init__(self, market_data, short_window: int = 5, long_window: int = 20, threshold: float = 0.001):
        self._md = market_data
        self.short_window = short_window
        self.long_window = long_window
        self.threshold = threshold

    def analyze(self, symbol: str) -> MarketSignal:
        lookback = max(self.short_window, self.long_window)
        prices: List[float] = self._md.get_recent_prices(symbol, lookback=lookback)

        if len(prices) < self.long_window:
            return MarketSignal(
                symbol=symbol,
                action="HOLD",
                confidence=0.0,
                reason=f"Not enough prices ({len(prices)}<{self.long_window})",
            )

        short = sum(prices[-self.short_window:]) / self.short_window
        long = sum(prices[-self.long_window:]) / self.long_window

        diff = (short - long) / long

        if diff > self.threshold:
            return MarketSignal(symbol, "BUY", 0.7, f"SMA{self.short_window} above SMA{self.long_window} ({short:.2f}>{long:.2f})")
        if diff < -self.threshold:
            return MarketSignal(symbol, "SELL", 0.7, f"SMA{self.short_window} below SMA{self.long_window} ({short:.2f}<{long:.2f})")

        return MarketSignal(symbol, "HOLD", 0.3, f"Close MAs ({short:.2f}≈{long:.2f})")
