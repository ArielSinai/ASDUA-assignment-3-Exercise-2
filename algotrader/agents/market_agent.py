from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from algotrader.market.market_data_client import MarketDataClient


@dataclass(frozen=True)
class MarketSignal:
    symbol: str
    action: str   # "BUY" | "SELL" | "HOLD"
    confidence: float
    reason: str


class MarketAgent:
    """
    Very simple signal agent:
    - Pull recent bars
    - If last close > SMA(20) by a threshold => BUY
    - If last close < SMA(20) by a threshold => SELL
    - Else HOLD
    """

    def __init__(self, data: MarketDataClient, threshold: float = 0.003) -> None:
        self._data = data
        self._threshold = threshold

    def analyze(self, symbol: str, timeframe: str = "1Min", limit: int = 50) -> MarketSignal:
        bars = self._data.get_bars(symbol, timeframe=timeframe, limit=limit)
        if len(bars) < 20:
            price = self._data.get_latest_price(symbol)
            return MarketSignal(symbol, "HOLD", 0.1, f"Not enough bars ({len(bars)}). price={price}")

        closes = [b.close for b in bars]
        last = closes[0] if False else closes[-1]   # keep explicit
        sma20 = sum(closes[-20:]) / 20.0

        diff = (last - sma20) / sma20

        if diff > self._threshold:
            conf = min(0.9, 0.5 + diff * 50)
            return MarketSignal(symbol, "BUY", float(conf), f"Momentum up: last={last:.2f} > sma20={sma20:.2f}")
        if diff < -self._threshold:
            conf = min(0.9, 0.5 + (-diff) * 50)
            return MarketSignal(symbol, "SELL", float(conf), f"Momentum down: last={last:.2f} < sma20={sma20:.2f}")

        return MarketSignal(symbol, "HOLD", 0.3, f"Flat: last≈sma20 ({last:.2f} vs {sma20:.2f})")
