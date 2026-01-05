from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Optional

from algotrader.agents.market_agent import MarketAgent
from algotrader.agents.risk_agent import RiskAgent
from algotrader.agents.exec_agent import ExecAgent
from algotrader.backtest.backtest_market_data import BacktestMarketData
from algotrader.backtest.backtest_execution import BacktestExecutionClient


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


def main() -> None:
    prices = {
        "PLTR": [1.0, 2.0, 3.0, 2.0, 1.0],
        "NFLX": [10.0, 10.0, 10.0, 10.0, 10.0],
        "PLTK": [5.0, 5.0, 5.0, 5.0, 5.0],
    }

    result = run_backtest(
        prices_by_symbol=prices,
        symbols=["PLTR", "NFLX", "PLTK"],
        short_window=2,
        long_window=3,
        threshold=0.0,
        risk_max_position_pct=1.0,
    )

    print("Backtest result:")
    print(f"  start_equity = {result.start_equity:.2f}")
    print(f"  end_equity   = {result.end_equity:.2f}")
    print(f"  trades       = {result.trades_executed}")
    print(f"  curve_len    = {len(result.equity_curve)}")


if __name__ == "__main__":
    main()
