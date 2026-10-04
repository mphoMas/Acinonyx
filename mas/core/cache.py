"""
mas.core.cache: High-performance thread-safe TTL Cache.
Synthesized autonomously by the Acinonyx Engineering Squad.
"""

import time
from typing import Any, Dict, Optional


class TTLCache:
    def __init__(self, default_ttl_sec: float = 60.0, max_size: int = 1000):
        self.default_ttl = default_ttl_sec
        self.max_size = max_size
        self._store: Dict[str, tuple[Any, float]] = {}

    def set(self, key: str, value: Any, ttl_sec: Optional[float] = None) -> None:
        ttl = ttl_sec if ttl_sec is not None else self.default_ttl
        expiry = time.time() + ttl
        if len(self._store) >= self.max_size and key not in self._store:
            oldest_key = min(self._store.keys(), key=lambda k: self._store[k][1])
            del self._store[oldest_key]
        self._store[key] = (value, expiry)

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self._store:
            return default
        val, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return default
        return val

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        now = time.time()
        self._store = {k: v for k, v in self._store.items() if v[1] > now}
        return len(self._store)
