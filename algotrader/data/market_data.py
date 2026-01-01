from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol, Any, Tuple
import json
import csv
from pathlib import Path

from algotrader.core.rate_limiter import RateLimiter


# -----------------------------
# Domain model
# -----------------------------

@dataclass(frozen=True)
class Bar:
    symbol: str
    timestamp: datetime  # UTC
    open: float
    high: float
    low: float
    close: float
    volume: float


# -----------------------------
# Interface
# -----------------------------

class MarketDataClient(Protocol):
    def get_recent_bars(
        self,
        symbol: str,
        limit: int = 60,
        timeframe: str = "1Min",
        now: Optional[datetime] = None,
    ) -> List[Bar]:
        """Return last `limit` bars up to `now` (UTC)."""


# -----------------------------
# Stub clients (dev/tests)
# -----------------------------

class StaticMarketDataClient:
    """
    Simple stub: returns pre-baked bars per symbol.
    Good for unit tests.
    """
    def __init__(self, bars_by_symbol: Dict[str, List[Bar]]):
        self._bars_by_symbol = bars_by_symbol

    def get_recent_bars(
        self,
        symbol: str,
        limit: int = 60,
        timeframe: str = "1Min",
        now: Optional[datetime] = None,
    ) -> List[Bar]:
        bars = self._bars_by_symbol.get(symbol, [])
        return bars[-limit:]


class CsvMarketDataClient:
    """
    Stub that loads bars from CSV.
    CSV columns expected (header):
      timestamp,open,high,low,close,volume
    timestamp should be ISO8601 (e.g. 2025-01-01T10:00:00Z)
    """
    def __init__(self, csv_paths_by_symbol: Dict[str, str]):
        self._paths = {k: Path(v) for k, v in csv_paths_by_symbol.items()}
        self._cache: Dict[str, List[Bar]] = {}

    def _load(self, symbol: str) -> List[Bar]:
        if symbol in self._cache:
            return self._cache[symbol]

        path = self._paths.get(symbol)
        if not path or not path.exists():
            self._cache[symbol] = []
            return []

        out: List[Bar] = []
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = _parse_ts(row["timestamp"])
                out.append(
                    Bar(
                        symbol=symbol,
                        timestamp=ts,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                )
        out.sort(key=lambda b: b.timestamp)
        self._cache[symbol] = out
        return out

    def get_recent_bars(
        self,
        symbol: str,
        limit: int = 60,
        timeframe: str = "1Min",
        now: Optional[datetime] = None,
    ) -> List[Bar]:
        bars = self._load(symbol)
        if not bars:
            return []

        if now is None:
            return bars[-limit:]

        now = _ensure_utc(now)
        eligible = [b for b in bars if b.timestamp <= now]
        return eligible[-limit:]


# -----------------------------
# Real client (Alpaca)
# -----------------------------

class AlpacaMarketDataClient:
    """
    Real client using Alpaca Market Data via alpaca-py.
    Install: pip install alpaca-py
    Env vars:
      ALPACA_API_KEY
      ALPACA_SECRET_KEY
    """
    def __init__(self, api_key: str, secret_key: str):
        from alpaca.data.historical import StockHistoricalDataClient
        self._client = StockHistoricalDataClient(api_key, secret_key)

    def get_recent_bars(
        self,
        symbol: str,
        limit: int = 60,
        timeframe: str = "1Min",
        now: Optional[datetime] = None,
    ) -> List[Bar]:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        now_dt = _ensure_utc(now) if now else datetime.now(timezone.utc)

        tf = _parse_timeframe(timeframe)  # supports "1Min", "5Min", "1Hour", "1Day"
        # Alpaca request: use limit only 
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            limit=limit,
        )
        resp = self._client.get_stock_bars(req)

        df = resp.df
        if df is None or len(df) == 0:
            return []

        out: List[Bar] = []
        try:
            for (sym, ts), row in df.iterrows():
                if sym != symbol:
                    continue
                out.append(
                    Bar(
                        symbol=sym,
                        timestamp=_ensure_utc(ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                )
        except Exception:
            for ts, row in df.iterrows():
                out.append(
                    Bar(
                        symbol=symbol,
                        timestamp=_ensure_utc(ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                )

        out = [b for b in out if b.timestamp <= now_dt]
        out.sort(key=lambda b: b.timestamp)
        return out[-limit:]


# -----------------------------
# Wrappers: Cache + RateLimiter
# -----------------------------

class CachedRateLimitedMarketDataClient:
    """
    Wrap any MarketDataClient:
      - Rate limit on each call
      - Cache by (symbol, limit, timeframe, now_bucket)
    """
    def __init__(
        self,
        inner: MarketDataClient,
        cache: Any,
        rate_limiter: RateLimiter,
        cache_ttl_seconds: int = 30,
        key_prefix: str = "marketdata",
    ):
        self._inner = inner
        self._cache = cache
        self._rl = rate_limiter
        self._ttl = cache_ttl_seconds
        self._prefix = key_prefix

    def get_recent_bars(
        self,
        symbol: str,
        limit: int = 60,
        timeframe: str = "1Min",
        now: Optional[datetime] = None,
    ) -> List[Bar]:
        now_dt = _ensure_utc(now) if now else datetime.now(timezone.utc)

        now_bucket = int(now_dt.timestamp() // 10)

        cache_key = f"{self._prefix}:recent:{symbol}:{timeframe}:{limit}:{now_bucket}"

        cached = _cache_get_json(self._cache, cache_key)
        if cached is not None:
            return [_bar_from_dict(d) for d in cached]

        self._rl.acquire(f"marketdata:get_recent_bars:{symbol}")

        bars = self._inner.get_recent_bars(symbol=symbol, limit=limit, timeframe=timeframe, now=now_dt)

        _cache_set_json(self._cache, cache_key, [asdict(b) for b in bars], ttl_seconds=self._ttl)
        return bars


# -----------------------------
# Helpers
# -----------------------------

def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _parse_ts(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return _ensure_utc(datetime.fromisoformat(s))

def _parse_timeframe(tf: str):
    from alpaca.data.timeframe import TimeFrame
    tf = tf.strip()

    mapping = {
        "1Min": TimeFrame.Minute,
        "5Min": TimeFrame(5, TimeFrame.Unit.Minute),
        "15Min": TimeFrame(15, TimeFrame.Unit.Minute),
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
    }
    if tf not in mapping:
        raise ValueError(f"Unsupported timeframe '{tf}'. Use one of: {list(mapping.keys())}")
    return mapping[tf]

def _bar_from_dict(d: Dict[str, Any]) -> Bar:
    ts = d["timestamp"]
    if isinstance(ts, str):
        ts = _parse_ts(ts)
    return Bar(
        symbol=d["symbol"],
        timestamp=ts,
        open=float(d["open"]),
        high=float(d["high"]),
        low=float(d["low"]),
        close=float(d["close"]),
        volume=float(d["volume"]),
    )

def _cache_get_json(cache: Any, key: str) -> Optional[Any]:
    """
    Expects your cache to have: get(key) -> Optional[str|bytes]
    """
    raw = cache.get(key)
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    return json.loads(raw)

def _cache_set_json(cache: Any, key: str, value: Any, ttl_seconds: int) -> None:
    """
    Expects your cache to have: set(key, value, ttl_seconds=...)
    """
    payload = json.dumps(value, default=str)
    # common signatures: set(key, value, ttl_seconds=...) OR set(key, value, ttl=...)
    try:
        cache.set(key, payload, ttl_seconds=ttl_seconds)
    except TypeError:
        cache.set(key, payload, ttl=ttl_seconds)
