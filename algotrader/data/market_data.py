from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Bar:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class StubMarketDataClient:
    """
    Test/dev stub expected by unit tests:
    - constructed with {symbol: [prices...]}
    - exposes get_recent_prices() + get_latest_price()
    - (optional) can also provide bars if you need later
    """
    def __init__(self, prices_by_symbol: Dict[str, List[float]]):
        self._prices = prices_by_symbol

    def get_recent_prices(self, symbol: str, limit: Optional[int] = None) -> List[float]:
        prices = self._prices.get(symbol, [])
        return prices if limit is None else prices[-limit:]

    def get_latest_price(self, symbol: str) -> Optional[float]:
        prices = self._prices.get(symbol, [])
        return prices[-1] if prices else None

    # optional helper (not required by tests)
    def get_recent_bars(
        self,
        symbol: str,
        limit: int = 60,
        timeframe: str = "1Min",
        now: Optional[datetime] = None,
    ) -> List[Bar]:
        prices = self.get_recent_prices(symbol, limit=limit)
        if not prices:
            return []
        base = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        out: List[Bar] = []
        for i, p in enumerate(prices):
            ts = base - timedelta(minutes=len(prices) - 1 - i)
            out.append(Bar(symbol, ts, p, p, p, p, 0.0))
        return out
