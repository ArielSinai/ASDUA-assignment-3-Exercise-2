
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataClient(ABC):
    """
    Abstract interface for market data.
    """

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> List[Bar]:
        pass

    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
        pass


class StubMarketDataClient(MarketDataClient):
    """
    Stub implementation for dev/tests (no real API calls).
    """

    def __init__(
        self,
        bars_by_symbol: Optional[Dict[str, List[Bar]]] = None,
        latest_prices: Optional[Dict[str, float]] = None,
    ) -> None:
        self._bars_by_symbol = bars_by_symbol or {}
        self._latest_prices = latest_prices or {}

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> List[Bar]:
        bars = self._bars_by_symbol.get(symbol, [])
        return [b for b in bars if start <= b.timestamp <= end]

    def get_latest_price(self, symbol: str) -> float:
        if symbol in self._latest_prices:
            return float(self._latest_prices[symbol])

        bars = self._bars_by_symbol.get(symbol, [])
        if bars:
            return float(bars[-1].close)

        raise ValueError(f"No price data available for symbol={symbol}")
