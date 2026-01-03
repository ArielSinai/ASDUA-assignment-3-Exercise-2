from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Protocol


@dataclass(frozen=True)
class Position:
    symbol: str
    qty: float
    avg_entry_price: float


@dataclass(frozen=True)
class Portfolio:
    cash: float
    positions: Dict[str, Position]


class ExecutionClient(Protocol):
    def get_portfolio(self) -> Portfolio: ...
    def get_position(self, symbol: str) -> Optional[Position]: ...
    def submit_market_order(self, symbol: str, qty: float, side: str) -> None:  # side: "buy"|"sell"
        ...
