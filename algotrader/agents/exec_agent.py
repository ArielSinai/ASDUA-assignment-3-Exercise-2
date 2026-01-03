from __future__ import annotations

from dataclasses import dataclass

from algotrader.agents.market_agent import MarketSignal
from algotrader.agents.risk_agent import RiskAgent
from algotrader.execution.execution_client import ExecutionClient


@dataclass(frozen=True)
class ExecResult:
    executed: bool
    reason: str


class ExecAgent:
    def __init__(self, execution: ExecutionClient, risk: RiskAgent):
        self._exec = execution
        self._risk = risk

    def act(self, signal: MarketSignal, trade_value: float) -> ExecResult:
        # Ignore HOLD
        if signal.action == "HOLD":
            return ExecResult(False, "HOLD signal")

        portfolio = self._exec.get_portfolio()
        pos = self._exec.get_position(signal.symbol)
        position_value = 0.0 if pos is None else pos.qty * pos.avg_entry_price

        proposed = trade_value if signal.action == "BUY" else -trade_value

        decision = self._risk.evaluate(
            symbol=signal.symbol,
            equity=portfolio.cash + sum(p.qty * p.avg_entry_price for p in portfolio.positions.values()),
            position_value=position_value,
            proposed_trade_value=proposed,
        )

        if not decision.allow_trade:
            return ExecResult(False, decision.reason)

        # For now qty is trade_value/1.0 because stub price=1.0
        qty = trade_value / 1.0
        side = "buy" if signal.action == "BUY" else "sell"
        self._exec.submit_market_order(signal.symbol, qty=qty, side=side)
        return ExecResult(True, f"Executed {side} {qty:.2f} {signal.symbol}")
