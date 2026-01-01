# algotrader/core/rate_limiter.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


class RateLimitExceeded(Exception):
    """
    Raised when a rate limit is exceeded.

    Attributes:
        retry_after_seconds: How long to wait (in seconds) until next attempt is likely to succeed.
        message: Human readable reason.
    """

    def __init__(self, retry_after_seconds: float, message: str = "Rate limit exceeded") -> None:
        super().__init__(f"{message}. retry_after_seconds={retry_after_seconds:.3f}")
        self.retry_after_seconds = float(retry_after_seconds)
        self.message = message


@dataclass
class _BucketCounter:
    bucket_id: int
    count: int


class RateLimiter:
    """
    Fixed-window rate limiter per key.

    Windows:
      - per_second: bucket = int(now)
      - per_hour:   bucket = int(now // 3600)
      - per_day:    bucket = int(now // 86400)

    Behavior matches tests like:
      calls at 0.10 and 0.20 consume the "second 0" bucket,
      a call at 1.05 is in "second 1" bucket and should be allowed.
    """

    def __init__(self, per_second: int, per_hour: int, per_day: int) -> None:
        if per_second <= 0 or per_hour <= 0 or per_day <= 0:
            raise ValueError("Rate limits must be positive integers")

        self.per_second = int(per_second)
        self.per_hour = int(per_hour)
        self.per_day = int(per_day)

        # key -> counters for each window
        self._sec: Dict[str, _BucketCounter] = {}
        self._hour: Dict[str, _BucketCounter] = {}
        self._day: Dict[str, _BucketCounter] = {}

    def acquire(self, key: str, now: Optional[float] = None) -> None:
        """
        Record a call for 'key' at time 'now' (seconds since epoch).
        Raises RateLimitExceeded if blocked.

        'now' is injectable for deterministic unit tests.
        """
        if now is None:
            import time
            now = time.time()

        # 1) per-second
        self._acquire_window(
            store=self._sec,
            key=key,
            bucket_id=int(now),
            limit=self.per_second,
            window_seconds=1.0,
            now=now,
            label="Per-second limit exceeded",
        )

        # 2) per-hour
        self._acquire_window(
            store=self._hour,
            key=key,
            bucket_id=int(now // 3600),
            limit=self.per_hour,
            window_seconds=3600.0,
            now=now,
            label="Per-hour limit exceeded",
        )

        # 3) per-day
        self._acquire_window(
            store=self._day,
            key=key,
            bucket_id=int(now // 86400),
            limit=self.per_day,
            window_seconds=86400.0,
            now=now,
            label="Per-day limit exceeded",
        )

    def _acquire_window(
        self,
        *,
        store: Dict[str, _BucketCounter],
        key: str,
        bucket_id: int,
        limit: int,
        window_seconds: float,
        now: float,
        label: str,
    ) -> None:
        counter = store.get(key)

        if counter is None or counter.bucket_id != bucket_id:
            counter = _BucketCounter(bucket_id=bucket_id, count=0)
            store[key] = counter

        if counter.count >= limit:
            retry_after = self._retry_after_fixed(bucket_id, window_seconds, now)
            raise RateLimitExceeded(retry_after, label)

        counter.count += 1

    @staticmethod
    def _retry_after_fixed(bucket_id: int, window_seconds: float, now: float) -> float:
        """
        For fixed window: wait until the next bucket starts.
        Example: second bucket_id=10 ends at t=11.0, so retry_after = 11.0 - now.
        """
        window_start = bucket_id * window_seconds
        window_end = window_start + window_seconds
        retry_after = window_end - now
        return max(0.0, float(retry_after))
