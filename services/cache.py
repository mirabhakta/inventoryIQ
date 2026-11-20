"""Small in-process TTL cache for the single-instance demo deployment.

The cache is intentionally process-local: Render runs one instance here, and
losing the cache on restart only costs a re-computation, never data.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """A thread-safe, size-bounded cache whose entries expire after a TTL."""

    def __init__(
        self,
        maxsize: int = 16,
        ttl_seconds: float = 900,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be at least 1.")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive.")

        self._maxsize = maxsize
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> T | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None

            expires_at, value = entry
            if expires_at <= self._clock():
                del self._entries[key]
                return None

            self._entries.move_to_end(key)
            return value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._entries[key] = (self._clock() + self._ttl_seconds, value)
            self._entries.move_to_end(key)

            while len(self._entries) > self._maxsize:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
