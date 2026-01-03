from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskDecision:
    allow_trade: bool
    max_position_pct: float  # e.g. 0.25 means up to 25% of equity per symbol
    reason: str


class RiskAgent:
    """
    Very minimal risk agent:
    - Caps maximum allocation per symbol as % of total equity.
    - Rejects trades if already above cap.
    """

    def __init__(self, max_position_pct: float = 0.25) -> None:
        if not (0.0 < max_position_pct <= 1.0):
            raise ValueError("max_position_pct must be in (0, 1].")
        self.max_position_pct = max_position_pct

    def evaluate(
        self,
        *,
        symbol: str,
        equity: float,
        position_value: float,
        proposed_trade_value: float,
    ) -> RiskDecision:
        """
        equity: total portfolio value (cash + positions)
        position_value: current $ value of this symbol position
        proposed_trade_value: $ value you want to add (buy) or reduce (sell; negative)
        """
        if equity <= 0:
            return RiskDecision(False, self.max_position_pct, "Invalid equity")

        new_position_value = position_value + proposed_trade_value

        # If selling/reducing, always allow from risk perspective
        if proposed_trade_value < 0:
            return RiskDecision(True, self.max_position_pct, "Reducing risk (sell)")

        cap_value = self.max_position_pct * equity
        if new_position_value > cap_value:
            return RiskDecision(
                False,
                self.max_position_pct,
                f"Position cap exceeded: new=${new_position_value:.2f} > cap=${cap_value:.2f}",
            )

        return RiskDecision(True, self.max_position_pct, "Within position cap")
