from __future__ import annotations

from typing import Optional, Dict, List

from algotrader.execution.execution_client import ExecutionClient, Portfolio, Position, OrderInfo


class AlpacaExecutionClient(ExecutionClient):
    """
    Alpaca execution client (paper/live) using alpaca-py.
    """

    def __init__(self, api_key: str, secret_key: str, paper: bool = True) -> None:
        try:
            from alpaca.trading.client import TradingClient
        except Exception as e:
            raise ImportError("alpaca-py is not installed. Run: pip install alpaca-py") from e

        self._client = TradingClient(api_key, secret_key, paper=paper)

    def get_portfolio(self) -> Portfolio:
        acct = self._client.get_account()

        cash = float(acct.cash)
        equity = float(acct.equity)

        positions: Dict[str, Position] = {}
        for p in self._client.get_all_positions():
            positions[p.symbol] = Position(
                symbol=p.symbol,
                qty=float(p.qty),
                avg_entry_price=float(p.avg_entry_price),
            )

        return Portfolio(cash=cash, equity=equity, positions=positions)

    def get_position(self, symbol: str) -> Optional[Position]:
        try:
            p = self._client.get_open_position(symbol)
        except Exception:
            return None

        return Position(
            symbol=p.symbol,
            qty=float(p.qty),
            avg_entry_price=float(p.avg_entry_price),
        )

    def list_open_orders(self, symbol: Optional[str] = None) -> List[OrderInfo]:
        # alpaca-py: get_orders(filter=GetOrdersRequest(...)) :contentReference[oaicite:1]{index=1}
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

        req = GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            symbols=[symbol] if symbol else None,
        )

        orders = self._client.get_orders(filter=req)

        out: List[OrderInfo] = []
        for o in orders:
            out.append(
                OrderInfo(
                    order_id=str(getattr(o, "id", "")),
                    symbol=str(getattr(o, "symbol", "")),
                    side=str(getattr(o, "side", "")),
                    status=str(getattr(o, "status", "")),
                    qty=float(getattr(o, "qty", 0.0)) if getattr(o, "qty", None) is not None else None,
                    notional=float(getattr(o, "notional", 0.0)) if getattr(o, "notional", None) is not None else None,
                )
            )
        return out

    def submit_market_order(self, symbol: str, qty: float, side: str) -> dict:
        """
        Treat qty as NOTIONAL USD amount (Alpaca supports notional orders for stocks).
        """
        side = side.lower().strip()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")
        if qty <= 0:
            raise ValueError("qty/notional must be positive")

        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        req = MarketOrderRequest(
            symbol=symbol,
            notional=float(qty),
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )

        order = self._client.submit_order(req)

        order_id = getattr(order, "id", None)
        status = getattr(order, "status", None)

        return {
            "order_id": str(order_id) if order_id is not None else None,
            "status": str(status) if status is not None else None,
        }
