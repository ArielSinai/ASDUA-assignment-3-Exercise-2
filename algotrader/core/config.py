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
    if v is None or not v.strip():
        return float(default)
    try:
        return float(v.strip())
    except ValueError:
        return float(default)


ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = _get_bool("ALPACA_PAPER", True)

MAX_EXISTING_POSITION_PCT_TO_ADD = _get_float("MAX_EXISTING_POSITION_PCT_TO_ADD", 0.10)
MIN_POSITION_PCT_TO_SELL = _get_float("MIN_POSITION_PCT_TO_SELL", 0.02)
