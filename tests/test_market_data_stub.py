from datetime import datetime, timedelta

from algotrader.data.market_data import Bar, StubMarketDataClient


def test_stub_market_data_returns_latest_price():
    now = datetime.utcnow()

    bars = [
        Bar(now - timedelta(minutes=2), 10, 11, 9, 10.5, 100),
        Bar(now - timedelta(minutes=1), 10.5, 12, 10, 11.5, 120),
    ]

    client = StubMarketDataClient(
        bars_by_symbol={"PLTR": bars}
    )

    assert client.get_latest_price("PLTR") == 11.5


def test_stub_market_data_filters_bars_by_time():
    now = datetime.utcnow()

    bars = [
        Bar(now - timedelta(minutes=10), 1, 1, 1, 1, 10),
        Bar(now - timedelta(minutes=1), 2, 2, 2, 2, 20),
    ]

    client = StubMarketDataClient(
        bars_by_symbol={"NFLX": bars}
    )

    result = client.get_bars(
        "NFLX",
        start=now - timedelta(minutes=5),
        end=now,
        timeframe="1Min",
    )

    assert len(result) == 1
    assert result[0].close == 2
