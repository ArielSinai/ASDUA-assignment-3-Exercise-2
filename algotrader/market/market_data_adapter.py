from __future__ import annotations

from typing import List

from .market_data_client import MarketDataClient


class BarsToPricesAdapter:
    def __init__(self, inner: MarketDataClient, timeframe: str = "1Min") -> None:
        self._inner = inner
        self._timeframe = timeframe

    def get_recent_prices(self, symbol: str, limit: int) -> List[float]:
        if limit <= 0:
            return []
        bars = self._inner.get_bars(symbol=symbol, timeframe=self._timeframe, limit=limit)
        return [float(b.close) for b in bars]
