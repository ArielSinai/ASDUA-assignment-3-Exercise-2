from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, List, Optional


@dataclass(frozen=True)
class Bar:
    ts: str         
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketDataClient(Protocol):
    def get_latest_price(self, symbol: str) -> float:
        ...

    def get_bars(
        self,
        symbol: str,
        timeframe: str,         
        limit: int = 100,
        start_iso: Optional[str] = None,
        end_iso: Optional[str] = None,
    ) -> List[Bar]:
        ...
