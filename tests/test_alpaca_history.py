from datetime import datetime, timezone

from algotrader.backtest.alpaca_history import bars_to_close_prices, make_week_window_utc
from algotrader.market.market_data_client import Bar


def test_bars_to_close_prices():
    bars = [
        Bar(ts="t1", open=1.0, high=2.0, low=0.5, close=1.5, volume=10),
        Bar(ts="t2", open=1.5, high=2.5, low=1.0, close=2.0, volume=20),
    ]
    assert bars_to_close_prices(bars) == [1.5, 2.0]


def test_make_week_window_utc_has_correct_order_and_duration():
    end = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    w = make_week_window_utc(end=end, days=7)
    assert w.start < w.end
    assert (w.end - w.start).days == 7
