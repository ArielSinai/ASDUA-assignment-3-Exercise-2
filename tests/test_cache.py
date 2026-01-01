import pytest
from algotrader.core.cache import TTLCache


def test_set_and_get_before_expiry():
    cache = TTLCache()

    cache.set("a", 123, ttl_seconds=10, now=0.0)
    assert cache.get("a", now=5.0) == 123


def test_get_returns_none_after_expiry():
    cache = TTLCache()

    cache.set("a", 123, ttl_seconds=10, now=0.0)
    assert cache.get("a", now=10.1) is None


def test_get_or_set_calls_supplier_once():
    cache = TTLCache()
    calls = []

    def supplier():
        calls.append(1)
        return "data"

    v1 = cache.get_or_set("k", ttl_seconds=10, supplier=supplier, now=0.0)
    v2 = cache.get_or_set("k", ttl_seconds=10, supplier=supplier, now=5.0)

    assert v1 == v2 == "data"
    assert len(calls) == 1


def test_get_or_set_recomputes_after_expiry():
    cache = TTLCache()
    calls = []

    def supplier():
        calls.append(1)
        return f"value-{len(calls)}"

    v1 = cache.get_or_set("k", ttl_seconds=5, supplier=supplier, now=0.0)
    v2 = cache.get_or_set("k", ttl_seconds=5, supplier=supplier, now=6.0)

    assert v1 != v2
    assert len(calls) == 2


def test_different_keys_are_independent():
    cache = TTLCache()

    cache.set("a", 1, ttl_seconds=10, now=0.0)
    cache.set("b", 2, ttl_seconds=10, now=0.0)

    assert cache.get("a", now=1.0) == 1
    assert cache.get("b", now=1.0) == 2
