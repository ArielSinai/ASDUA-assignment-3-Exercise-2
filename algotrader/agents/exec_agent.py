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
        if signal.action == "HOLD":
            return ExecResult(False, "HOLD signal")

        open_orders = self._exec.list_open_orders(signal.symbol)
        if open_orders:
            o = open_orders[0]
            return ExecResult(
                False,
                f"Open order exists: symbol={o.symbol} side={o.side} status={o.status} id={o.order_id}"
            )

        portfolio = self._exec.get_portfolio()
        pos = self._exec.get_position(signal.symbol)
        position_value = 0.0 if pos is None else pos.qty * pos.avg_entry_price

        proposed = trade_value if signal.action == "BUY" else -trade_value

        decision = self._risk.evaluate(
            symbol=signal.symbol,
            equity=portfolio.equity,
            position_value=position_value,
            proposed_trade_value=proposed,
        )

        if not decision.allow_trade:
            return ExecResult(False, f"Risk blocked: {decision.reason}")

        if signal.action == "SELL" and (pos is None or pos.qty <= 0):
            return ExecResult(False, "No position to sell")

       
        sized_value = abs(float(decision.approved_trade_value))

        if sized_value <= 0:
            return ExecResult(False, "Trade size is zero after risk sizing")

        side = "buy" if signal.action == "BUY" else "sell"

        try:
            resp = self._exec.submit_market_order(
                signal.symbol,
                qty=sized_value,
                side=side,
            )

            if isinstance(resp, dict):
                oid = resp.get("order_id")
                st = resp.get("status")
                return ExecResult(
                    True,
                    f"Submitted {side} ${sized_value:.2f} {signal.symbol} (order_id={oid}, status={st})",
                )

            return ExecResult(True, f"Executed {side} {sized_value:.2f} {signal.symbol}")

        except Exception as e:
            return ExecResult(False, f"Execution error: {e}")
