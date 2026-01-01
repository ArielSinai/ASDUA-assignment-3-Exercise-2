import pytest
from algotrader.core.rate_limiter import RateLimiter, RateLimitExceeded


def test_allows_within_limits():
    rl = RateLimiter(per_second=2, per_hour=10, per_day=100)

    rl.acquire("serpapi", now=0.00)
    rl.acquire("serpapi", now=0.10)  


def test_blocks_third_call_same_second():
    rl = RateLimiter(per_second=2, per_hour=10, per_day=100)

    rl.acquire("serpapi", now=0.00)
    rl.acquire("serpapi", now=0.20)

    with pytest.raises(RateLimitExceeded) as e:
        rl.acquire("serpapi", now=0.30)

    assert e.value.retry_after_seconds > 0


def test_hour_limit_blocks():
    rl = RateLimiter(per_second=100, per_hour=3, per_day=100)

    rl.acquire("alpaca", now=0)
    rl.acquire("alpaca", now=10)
    rl.acquire("alpaca", now=20)

    with pytest.raises(RateLimitExceeded):
        rl.acquire("alpaca", now=30)


def test_day_limit_blocks():
    rl = RateLimiter(per_second=100, per_hour=100, per_day=2)

    rl.acquire("news", now=0)
    rl.acquire("news", now=100)

    with pytest.raises(RateLimitExceeded):
        rl.acquire("news", now=200)


def test_resets_second_window():
    rl = RateLimiter(per_second=2, per_hour=10, per_day=100)

    rl.acquire("x", now=0.10)
    rl.acquire("x", now=0.20)

    rl.acquire("x", now=1.05) 


def test_independent_keys():
    rl = RateLimiter(per_second=1, per_hour=10, per_day=100)

    rl.acquire("serpapi", now=0.1)
    rl.acquire("alpaca", now=0.2)  
