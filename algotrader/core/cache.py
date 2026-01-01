from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


def make_cache_key(*parts: Any) -> str:
    """
    Make a stable string cache key from parts.
    Keep it simple + deterministic for this assignment.
    """
    return "|".join(str(p) for p in parts)


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """
    Simple in-memory TTL cache.

    - now is injectable for deterministic unit tests
    - not thread-safe (good enough for this assignment)
    """

    def __init__(self) -> None:
        self._store: Dict[str, _CacheEntry] = {}

    def get(self, key: str, now: Optional[float] = None) -> Any | None:
        if now is None:
            import time
            now = time.time()

        entry = self._store.get(key)
        if entry is None:
            return None

        if now >= entry.expires_at:
            del self._store[key]
            return None

        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: float, now: Optional[float] = None) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        if now is None:
            import time
            now = time.time()

        expires_at = now + ttl_seconds
        self._store[key] = _CacheEntry(value=value, expires_at=expires_at)

    def get_or_set(
        self,
        key: str,
        ttl_seconds: float,
        supplier: Callable[[], Any],
        now: Optional[float] = None,
    ) -> Any:
        existing = self.get(key, now=now)
        if existing is not None:
            return existing

        value = supplier()
        self.set(key, value, ttl_seconds=ttl_seconds, now=now)
        return value
