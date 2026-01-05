from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizing:
    notional_usd: float
    reason: str


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def size_trade_notional(
    *,
    equity: float,
    max_position_pct: float,
    existing_position_value: float,
    desired_trade_usd: float,
    min_trade_usd: float = 50.0,
) -> PositionSizing:
    if equity <= 0:
        return PositionSizing(0.0, "Invalid equity")

    cap = max_position_pct * equity
    remaining = cap - existing_position_value

    if remaining <= 0:
        return PositionSizing(0.0, "No remaining capacity under cap")

    notional = min(desired_trade_usd, remaining)
    notional = clamp(notional, 0.0, desired_trade_usd)

    if notional < min_trade_usd:
        return PositionSizing(0.0, f"Trade too small (<{min_trade_usd}) under cap")

    return PositionSizing(float(notional), "Sized under cap")
