from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from algotrader.core.cache import TTLCache, make_cache_key
from algotrader.core.rate_limiter import RateLimiter

from .news_data import NewsDataClient, NewsItem


class CachedRateLimitedNewsDataClient(NewsDataClient):
    def __init__(
        self,
        inner: NewsDataClient,
        cache: TTLCache,
        rate_limiter: RateLimiter,
        cache_ttl_seconds: float = 300.0,
        limiter_key_prefix: str = "news",
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._rl = rate_limiter
        self._ttl = float(cache_ttl_seconds)
        self._prefix = str(limiter_key_prefix)

    def get_recent_news(
        self,
        symbol: str,
        *,
        as_of: datetime,
        lookback_days: int = 7,
        limit: int = 20,
        now: Optional[float] = None,
    ) -> List[NewsItem]:
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        key = make_cache_key(
            "recent_news",
            {"symbol": symbol, "as_of": as_of.isoformat(), "lookback_days": int(lookback_days), "limit": int(limit)},
        )

        def supplier() -> List[NewsItem]:
            self._rl.acquire(f"{self._prefix}:recent_news", now=now)
            return list(
                self._inner.get_recent_news(
                    symbol,
                    as_of=as_of,
                    lookback_days=int(lookback_days),
                    limit=int(limit),
                )
            )

        return list(self._cache.get_or_set(key, ttl_seconds=self._ttl, supplier=supplier, now=now))
