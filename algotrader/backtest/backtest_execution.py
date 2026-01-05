from __future__ import annotations

from dataclasses import replace
from typing import Dict, Optional

from algotrader.execution.execution_client import ExecutionClient, Portfolio, Position
from algotrader.backtest.backtest_market_data import BacktestMarketData


class BacktestExecutionClient(ExecutionClient):
    def __init__(self, market_data: BacktestMarketData, starting_cash: float = 100_000.0):
        self._md = market_data
        self._cash = float(starting_cash)
        self._positions: Dict[str, Position] = {}

    def get_portfolio(self) -> Portfolio:
        equity = float(self._cash)
        for sym, pos in self._positions.items():
            px = self._md.get_latest_price(sym)
            if px is None:
                px = pos.avg_entry_price
            equity += float(pos.qty) * float(px)
        return Portfolio(cash=float(self._cash), equity=float(equity), positions=dict(self._positions))

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)

    def submit_market_order(self, symbol: str, qty: float, side: str) -> None:
        side = side.lower().strip()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")
        if qty <= 0:
            raise ValueError("qty/notional must be positive")

        px = self._md.get_latest_price(symbol)
        if px is None or px <= 0:
            raise ValueError("missing/invalid latest price")

        notional = float(qty)

        if side == "buy":
            spend = min(notional, self._cash)
            if spend <= 0:
                raise ValueError("insufficient cash")
            shares = spend / float(px)

            self._cash -= spend
            pos = self._positions.get(symbol)
            if pos is None:
                self._positions[symbol] = Position(symbol=symbol, qty=float(shares), avg_entry_price=float(px))
            else:
                new_qty = float(pos.qty) + float(shares)
                new_avg = ((float(pos.qty) * float(pos.avg_entry_price)) + (float(shares) * float(px))) / new_qty
                self._positions[symbol] = replace(pos, qty=float(new_qty), avg_entry_price=float(new_avg))
            return

        pos = self._positions.get(symbol)
        if pos is None or pos.qty <= 0:
            raise ValueError("insufficient position")

        position_value = float(pos.qty) * float(px)
        sell_notional = min(notional, position_value)
        shares_to_sell = sell_notional / float(px)

        if shares_to_sell > float(pos.qty):
            shares_to_sell = float(pos.qty)
            sell_notional = shares_to_sell * float(px)

        self._cash += sell_notional
        new_qty = float(pos.qty) - float(shares_to_sell)

        if new_qty <= 1e-12:
            del self._positions[symbol]
        else:
            self._positions[symbol] = replace(pos, qty=float(new_qty))
