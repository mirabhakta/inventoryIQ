import pytest

from services.cache import TTLCache


def test_get_missing_key_returns_none() -> None:
    assert TTLCache().get("missing") is None


def test_set_then_get_returns_the_value() -> None:
    cache = TTLCache()
    cache.set("file.csv", {"rows": 10})

    assert cache.get("file.csv") == {"rows": 10}


def test_entry_expires_after_the_ttl() -> None:
    now = [0.0]
    cache = TTLCache(ttl_seconds=10, clock=lambda: now[0])
    cache.set("key", "value")

    now[0] = 9.9
    assert cache.get("key") == "value"

    now[0] = 10.0
    assert cache.get("key") is None


def test_oldest_entry_is_evicted_at_capacity() -> None:
    cache = TTLCache(maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_get_refreshes_recency() -> None:
    cache = TTLCache(maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")
    cache.set("c", 3)

    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_clear_removes_every_entry() -> None:
    cache = TTLCache()
    cache.set("a", 1)
    cache.clear()

    assert cache.get("a") is None
    assert len(cache) == 0


def test_rejects_non_positive_capacity() -> None:
    with pytest.raises(ValueError, match="maxsize"):
        TTLCache(maxsize=0)
