from algotrader.backtest.backtest_market_data import BacktestMarketData
from algotrader.backtest.backtest_execution import BacktestExecutionClient
from algotrader.backtest.backtest_runner import run_backtest


def test_backtest_market_data_recent_prices_and_latest():
    md = BacktestMarketData({"PLTR": [1, 2, 3, 4, 5]})
    md.set_index(2)
    assert md.get_latest_price("PLTR") == 3.0
    assert md.get_recent_prices("PLTR", limit=2) == [2, 3]
    assert md.get_recent_prices("PLTR", limit=10) == [1, 2, 3]


def test_backtest_execution_buy_and_sell_notional_clamped():
    md = BacktestMarketData({"PLTR": [1.0, 1.0, 0.25]})
    ex = BacktestExecutionClient(md, starting_cash=100_000.0)

    md.set_index(0)
    ex.submit_market_order("PLTR", qty=1000.0, side="buy")
    p = ex.get_position("PLTR")
    assert p is not None
    assert abs(p.qty - 1000.0) < 1e-6
    assert abs(ex.get_portfolio().cash - 99_000.0) < 1e-6

    md.set_index(2)
    ex.submit_market_order("PLTR", qty=1000.0, side="sell")
    p2 = ex.get_position("PLTR")
    assert p2 is None
    assert abs(ex.get_portfolio().cash - 99_250.0) < 1e-6


def test_run_backtest_produces_equity_curve_and_trades():
    prices = {
        "PLTR": [1.0, 2.0, 1.0, 0.5, 0.25],
        "NFLX": [10.0, 10.0, 10.0, 10.0, 10.0],
        "PLTK": [5.0, 5.0, 5.0, 5.0, 5.0],
    }

    res = run_backtest(
        prices_by_symbol=prices,
        symbols=["PLTR", "NFLX", "PLTK"],
        starting_cash=100_000.0,
        trade_value_usd=1000.0,
        short_window=2,
        long_window=3,
        threshold=0.0,
        risk_max_position_pct=1.0,
    )

    assert res.start_equity == 100_000.0
    assert len(res.equity_curve) >= 2
    assert res.trades_executed >= 1
    assert res.end_equity > 0
