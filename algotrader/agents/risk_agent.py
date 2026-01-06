from __future__ import annotations

from dataclasses import dataclass

from algotrader.tools.calculator_tool import size_trade_notional


@dataclass(frozen=True)
class RiskDecision:
    allow_trade: bool
    max_position_pct: float
    approved_trade_value: float
    reason: str


class RiskAgent:
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
        """Strict risk gate (no sizing).

        - For BUY: blocks if the resulting position would exceed max_position_pct of equity.
        - For SELL: always allowed (risk-reducing).
        """
        if equity <= 0:
            return RiskDecision(False, self.max_position_pct, 0.0, "Invalid equity")

        if proposed_trade_value < 0:
            return RiskDecision(True, self.max_position_pct, proposed_trade_value, "Reducing risk (sell)")

        cap = equity * self.max_position_pct
        if position_value + proposed_trade_value > cap:
            return RiskDecision(False, self.max_position_pct, 0.0, "Position cap exceeded")

        return RiskDecision(True, self.max_position_pct, proposed_trade_value, "Approved")

    def approve_and_size(
        self,
        *,
        symbol: str,
        equity: float,
        position_value: float,
        proposed_trade_value: float,
        min_trade_usd: float = 50.0,
    ) -> RiskDecision:
        """Approve and (optionally) reduce trade size to fit the position cap."""
        if equity <= 0:
            return RiskDecision(False, self.max_position_pct, 0.0, "Invalid equity")

        if proposed_trade_value < 0:
            return RiskDecision(True, self.max_position_pct, proposed_trade_value, "Reducing risk (sell)")

        sizing = size_trade_notional(
            equity=equity,
            max_position_pct=self.max_position_pct,
            existing_position_value=position_value,
            desired_trade_usd=proposed_trade_value,
            min_trade_usd=min_trade_usd,
        )

        if sizing.notional_usd <= 0:
            return RiskDecision(False, self.max_position_pct, 0.0, sizing.reason)

        return RiskDecision(True, self.max_position_pct, float(sizing.notional_usd), "Approved and sized")
