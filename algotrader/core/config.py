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


def _get_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _get_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip()


ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = _get_bool("ALPACA_PAPER", True)

MAX_EXISTING_POSITION_PCT_TO_ADD = _get_float("MAX_EXISTING_POSITION_PCT_TO_ADD", 0.10)
MIN_POSITION_PCT_TO_SELL = _get_float("MIN_POSITION_PCT_TO_SELL", 0.02)

COOLDOWN_SECONDS = _get_float("COOLDOWN_SECONDS", 5.0)
TAKE_PROFIT_PCT = _get_float("TAKE_PROFIT_PCT", 0.05)
STOP_LOSS_PCT = _get_float("STOP_LOSS_PCT", 0.03)

BACKTEST_START = _get_str("BACKTEST_START", "")
BACKTEST_END = _get_str("BACKTEST_END", "")
BACKTEST_TIMEFRAME = _get_str("BACKTEST_TIMEFRAME", "1Hour")

USE_REAL_NEWS = _get_bool("USE_REAL_NEWS", True)
NEWS_CACHE_TTL_SECONDS = _get_float("NEWS_CACHE_TTL_SECONDS", 300.0)
NEWS_LOOKBACK_DAYS = _get_int("NEWS_LOOKBACK_DAYS", 7)
NEWS_LIMIT = _get_int("NEWS_LIMIT", 10)

NEWS_STRONG_THRESHOLD = _get_float("NEWS_STRONG_THRESHOLD", 0.60)
NEWS_MIN_CONF_FOR_SIGNAL = _get_float("NEWS_MIN_CONF_FOR_SIGNAL", 0.60)