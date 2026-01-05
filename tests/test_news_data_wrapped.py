import pytest
from datetime import datetime, timezone

from algotrader.core.cache import TTLCache
from algotrader.core.rate_limiter import RateLimiter, RateLimitExceeded
from algotrader.data.news_data import NewsItem, StubNewsDataClient
from algotrader.data.news_data_wrapped import CachedRateLimitedNewsDataClient


def test_cached_news_client_caches_results():
    as_of = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)

    stub = StubNewsDataClient(
        items_by_symbol={
            "PLTR": [NewsItem("PLTR", as_of, "A", 0.1)]
        }
    )

    cache = TTLCache()
    rl = RateLimiter(per_second=1, per_hour=100, per_day=1000)
    wrapped = CachedRateLimitedNewsDataClient(stub, cache, rl, cache_ttl_seconds=60.0)

    r1 = wrapped.get_recent_news("PLTR", as_of=as_of, lookback_days=7, limit=10, now=0.0)
    r2 = wrapped.get_recent_news("PLTR", as_of=as_of, lookback_days=7, limit=10, now=0.0)

    assert r1 == r2


def test_cached_news_client_rate_limits_on_cache_miss():
    as_of = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)

    stub = StubNewsDataClient(
        items_by_symbol={
            "PLTR": [NewsItem("PLTR", as_of, "A", 0.1)]
        }
    )

    cache = TTLCache()
    rl = RateLimiter(per_second=1, per_hour=100, per_day=1000)
    wrapped = CachedRateLimitedNewsDataClient(stub, cache, rl, cache_ttl_seconds=60.0)

    wrapped.get_recent_news("PLTR", as_of=as_of, lookback_days=7, limit=10, now=0.0)

    with pytest.raises(RateLimitExceeded):
        wrapped.get_recent_news("NFLX", as_of=as_of, lookback_days=7, limit=10, now=0.0)
