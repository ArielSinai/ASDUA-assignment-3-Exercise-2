from __future__ import annotations

from typing import List, Optional

from algotrader.market.market_data_adapter import BarsToPricesAdapter
from algotrader.market.market_data_client import Bar, MarketDataClient


class FakeMarketDataClient(MarketDataClient):
    def __init__(self, closes: List[float]) -> None:
        self._closes = closes

    def get_latest_price(self, symbol: str) -> float:
        return float(self._closes[-1]) if self._closes else 0.0

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        start_iso: Optional[str] = None,
        end_iso: Optional[str] = None,
    ) -> List[Bar]:
        out = []
        for i, c in enumerate(self._closes[:limit]):
            out.append(Bar(ts=f"t{i}", open=c, high=c, low=c, close=c, volume=1))
        return out


def test_adapter_returns_close_prices_in_order():
    client = FakeMarketDataClient([10.0, 11.0, 12.5])
    adapter = BarsToPricesAdapter(client, timeframe="1Min")
    assert adapter.get_recent_prices("PLTR", 3) == [10.0, 11.0, 12.5]


def test_adapter_returns_empty_when_limit_non_positive():
    client = FakeMarketDataClient([10.0, 11.0])
    adapter = BarsToPricesAdapter(client)
    assert adapter.get_recent_prices("PLTR", 0) == []
    assert adapter.get_recent_prices("PLTR", -5) == []


def test_adapter_returns_available_if_less_than_limit():
    client = FakeMarketDataClient([1.0, 2.0])
    adapter = BarsToPricesAdapter(client)
    assert adapter.get_recent_prices("PLTR", 10) == [1.0, 2.0]


def test_adapter_latest_price_delegates():
    client = FakeMarketDataClient([7.0, 8.5, 9.25])
    adapter = BarsToPricesAdapter(client)
    assert adapter.get_latest_price("PLTR") == 9.25
