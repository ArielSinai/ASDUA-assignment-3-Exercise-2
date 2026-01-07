from __future__ import annotations

from typing import List

from .market_data_client import MarketDataClient


class BarsToPricesAdapter:
    def __init__(self, bars_client: MarketDataClient, timeframe: str = "1Min", limit: int = 60) -> None:
        self._bars = bars_client
        self.timeframe = str(timeframe)
        self.limit = int(limit)

    def get_recent_prices(self, symbol: str, lookback: int) -> List[float]:
        n = max(int(lookback), 1)
        bars = self._bars.get_bars(symbol, timeframe=self.timeframe, limit=max(self.limit, n))
        
        if not bars:
            return []
        
        closes = [float(b.close) for b in bars]
        return closes[-n:]

    def get_last_price(self, symbol: str) -> float:
        prices = self.get_recent_prices(symbol, 1)
        
        if not prices:
            raise ValueError(f"No market data available for {symbol}. Market might be closed or data unavailable.")
        
        return float(prices[-1])