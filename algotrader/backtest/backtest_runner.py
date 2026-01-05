from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Sequence, Optional

from algotrader.agents.market_agent import MarketAgent
from algotrader.agents.risk_agent import RiskAgent
from algotrader.agents.exec_agent import ExecAgent

from algotrader.core.config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    BACKTEST_START,
    BACKTEST_END,
    BACKTEST_TIMEFRAME,
)

from algotrader.backtest.backtest_market_data import BacktestMarketData
from algotrader.backtest.backtest_execution import BacktestExecutionClient
from algotrader.backtest.alpaca_history import fetch_prices_by_symbol, make_week_window_utc, BacktestWindow
from algotrader.market.market_data_alpaca import AlpacaMarketDataClient


@dataclass(frozen=True)
class BacktestResult:
    start_equity: float
    end_equity: float
    trades_executed: int
    equity_curve: List[float]


def run_backtest(
    *,
    prices_by_symbol: Dict[str, List[float]],
    symbols: Sequence[str],
    starting_cash: float = 100_000.0,
    trade_value_usd: float = 1000.0,
    short_window: int = 5,
    long_window: int = 20,
    threshold: float = 0.001,
    risk_max_position_pct: float = 0.25,
    max_steps: Optional[int] = None,
) -> BacktestResult:
    md = BacktestMarketData(prices_by_symbol)
    ex = BacktestExecutionClient(md, starting_cash=starting_cash)
    market_agent = MarketAgent(md, short_window=short_window, long_window=long_window, threshold=threshold)
    risk_agent = RiskAgent(max_position_pct=risk_max_position_pct)
    exec_agent = ExecAgent(execution=ex, risk=risk_agent)

    steps = md.max_steps()
    if max_steps is not None:
        steps = min(steps, int(max_steps))

    start_equity = ex.get_portfolio().equity
    equity_curve: List[float] = [float(start_equity)]
    trades = 0

    for i in range(steps):
        md.set_index(i)

        for sym in symbols:
            signal = market_agent.analyze(sym)
            pos = ex.get_position(sym)

            if signal.action == "BUY" and pos is not None and pos.qty > 0:
                continue
            if signal.action == "SELL" and (pos is None or pos.qty <= 0):
                continue

            res = exec_agent.act(signal, trade_value=float(trade_value_usd))
            if res.executed:
                trades += 1

        equity_curve.append(float(ex.get_portfolio().equity))

    end_equity = float(ex.get_portfolio().equity)
    return BacktestResult(
        start_equity=float(start_equity),
        end_equity=float(end_equity),
        trades_executed=int(trades),
        equity_curve=equity_curve,
    )


def _parse_iso_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def main() -> None:
    symbols = ["PLTR", "NFLX", "PLTK"]
    use_alpaca = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    if use_alpaca:
        md = AlpacaMarketDataClient(api_key=ALPACA_API_KEY, api_secret=ALPACA_SECRET_KEY)

        if BACKTEST_START and BACKTEST_END:
            window = BacktestWindow(start=_parse_iso_dt(BACKTEST_START), end=_parse_iso_dt(BACKTEST_END))
            source = f"Alpaca ({BACKTEST_START} to {BACKTEST_END}, {BACKTEST_TIMEFRAME})"
        else:
            window = make_week_window_utc(days=7)
            source = f"Alpaca (last 7 days, {BACKTEST_TIMEFRAME})"

        prices = fetch_prices_by_symbol(
            md=md,
            symbols=symbols,
            window=window,
            timeframe=BACKTEST_TIMEFRAME,
            limit=1000,
        )
    else:
        prices = {
            "PLTR": [1.0, 2.0, 3.0, 2.0, 1.0],
            "NFLX": [10.0, 10.0, 10.0, 10.0, 10.0],
            "PLTK": [5.0, 5.0, 5.0, 5.0, 5.0],
        }
        source = "Toy sample data"

    result = run_backtest(
        prices_by_symbol=prices,
        symbols=symbols,
        starting_cash=100_000.0,
        trade_value_usd=1000.0,
        short_window=5,
        long_window=20,
        threshold=0.001,
        risk_max_position_pct=0.25,
    )

    print("Backtest result:")
    print(f"  source       = {source}")
    print(f"  start_equity = {result.start_equity:.2f}")
    print(f"  end_equity   = {result.end_equity:.2f}")
    print(f"  trades       = {result.trades_executed}")
    print(f"  curve_len    = {len(result.equity_curve)}")


if __name__ == "__main__":
    main()
