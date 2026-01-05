from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Protocol, List


@dataclass(frozen=True)
class Position:
    symbol: str
    qty: float
    avg_entry_price: float


@dataclass(frozen=True)
class Portfolio:
    cash: float
    equity: float
    positions: Dict[str, Position]


@dataclass(frozen=True)
class OrderInfo:
    order_id: str
    symbol: str
    side: str
    status: str
    qty: Optional[float] = None
    notional: Optional[float] = None


class ExecutionClient(Protocol):
    def get_portfolio(self) -> Portfolio: ...
    def get_position(self, symbol: str) -> Optional[Position]: ...

    def submit_market_order(self, symbol: str, qty: float, side: str) -> object: ...

    def list_open_orders(self, symbol: Optional[str] = None) -> List[OrderInfo]: ...
