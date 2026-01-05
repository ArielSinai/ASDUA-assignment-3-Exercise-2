from __future__ import annotations

from typing import Dict, List, Optional


class BacktestMarketData:
    def __init__(self, prices_by_symbol: Dict[str, List[float]]):
        self._prices = prices_by_symbol
        self._i = 0

    def set_index(self, i: int) -> None:
        self._i = i

    def max_steps(self) -> int:
        if not self._prices:
            return 0
        return min(len(v) for v in self._prices.values())

    def get_recent_prices(self, symbol: str, limit: Optional[int] = None) -> List[float]:
        series = self._prices.get(symbol, [])
        end = min(self._i + 1, len(series))
        data = series[:end]
        if limit is None:
            return list(data)
        return list(data[-limit:])

    def get_latest_price(self, symbol: str) -> Optional[float]:
        series = self._prices.get(symbol, [])
        if not series:
            return None
        idx = min(self._i, len(series) - 1)
        return float(series[idx])
