from dotenv import load_dotenv
load_dotenv()

import os


def _get_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default


ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = _get_bool("ALPACA_PAPER", True)

MAX_EXISTING_POSITION_PCT_TO_ADD = _get_float(
    "MAX_EXISTING_POSITION_PCT_TO_ADD", 0.10
)

MIN_POSITION_PCT_TO_SELL = _get_float(
    "MIN_POSITION_PCT_TO_SELL", 0.02
)

COOLDOWN_SECONDS = _get_float(
    "COOLDOWN_SECONDS", 15.0
)

TAKE_PROFIT_PCT = _get_float(
    "TAKE_PROFIT_PCT", 0.03
)

STOP_LOSS_PCT = _get_float(
    "STOP_LOSS_PCT", 0.02
)
