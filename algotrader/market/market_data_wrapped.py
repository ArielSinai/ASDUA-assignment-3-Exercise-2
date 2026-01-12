from __future__ import annotations

from typing import List, Optional

from algotrader.core.cache import TTLCache, make_cache_key
from algotrader.core.rate_limiter import RateLimiter

from .market_data_client import Bar, MarketDataClient


class CachedRateLimitedMarketDataClient(MarketDataClient):
    def __init__(
        self,
        inner: MarketDataClient,
        cache: TTLCache,
        rate_limiter: RateLimiter,
        cache_ttl_seconds_latest_price: float = 2.0,
        cache_ttl_seconds_bars: float = 60.0,
        limiter_key_prefix: str = "marketdata",
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._rl = rate_limiter
        self._ttl_price = cache_ttl_seconds_latest_price
        self._ttl_bars = cache_ttl_seconds_bars
        self._prefix = limiter_key_prefix

    def get_latest_price(self, symbol: str) -> float:
        key = make_cache_key("latest_price", {"symbol": symbol})

        def supplier() -> float:
            self._rl.acquire(f"{self._prefix}:latest_price:{symbol}")
            price = self._inner.get_latest_price(symbol)
            if price is None:  
                raise ValueError(f"No latest price for {symbol}")
            return float(price)

        return float(self._cache.get_or_set(key, ttl_seconds=self._ttl_price, supplier=supplier))

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        start_iso: Optional[str] = None,
        end_iso: Optional[str] = None,
    ) -> List[Bar]:
        key = make_cache_key(
            "bars",
            {"symbol": symbol, "timeframe": timeframe, "limit": limit, "start": start_iso, "end": end_iso},
        )

        def supplier() -> List[Bar]:
            self._rl.acquire(f"{self._prefix}:bars:{symbol}:{timeframe}")
            bars = self._inner.get_bars(symbol, timeframe, limit=limit, start_iso=start_iso, end_iso=end_iso)
            if bars is None: 
                return []
            return list(bars)

        return list(self._cache.get_or_set(key, ttl_seconds=self._ttl_bars, supplier=supplier))
