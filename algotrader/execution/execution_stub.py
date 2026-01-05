from __future__ import annotations

from dataclasses import replace
from typing import Dict, Optional

from algotrader.execution.execution_client import ExecutionClient, Portfolio, Position

from algotrader.execution.execution_client import OrderInfo

class StubExecutionClient(ExecutionClient):
    def __init__(self, starting_cash: float = 100_000.0):
        self._cash = float(starting_cash)
        self._positions: Dict[str, Position] = {}

    def get_portfolio(self) -> Portfolio:
        equity = self._cash
        return Portfolio(
            cash=self._cash,
            equity=equity,
            positions=dict(self._positions),
        )

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)

    def list_open_orders(self, symbol: str) -> list[dict]:
        return []

    def submit_market_order(self, symbol: str, qty: float, side: str) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        side = side.lower().strip()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")

        price = 1.0
        cost = qty * price

        if side == "buy":
            if cost > self._cash:
                raise ValueError("insufficient cash")
            self._cash -= cost
            pos = self._positions.get(symbol)
            if pos is None:
                self._positions[symbol] = Position(symbol=symbol, qty=qty, avg_entry_price=price)
            else:
                new_qty = pos.qty + qty
                new_avg = ((pos.qty * pos.avg_entry_price) + (qty * price)) / new_qty
                self._positions[symbol] = replace(pos, qty=new_qty, avg_entry_price=new_avg)

        else:
            pos = self._positions.get(symbol)
            if pos is None or pos.qty < qty:
                raise ValueError("insufficient position")
            self._cash += cost
            new_qty = pos.qty - qty
            if new_qty == 0:
                del self._positions[symbol]
            else:
                self._positions[symbol] = replace(pos, qty=new_qty)

    def list_open_orders(self, symbol: Optional[str] = None) -> list[OrderInfo]:
        return []