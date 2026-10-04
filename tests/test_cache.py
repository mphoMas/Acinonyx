import time
import unittest
from mas.core.cache import TTLCache


class TestTTLCache(unittest.TestCase):
    def test_cache_set_get_and_expiration(self):
        cache = TTLCache(default_ttl_sec=0.1, max_size=2)
        cache.set("a", 100)
        self.assertEqual(cache.get("a"), 100)
        time.sleep(0.15)
        self.assertIsNone(cache.get("a"))

    def test_cache_eviction(self):
        cache = TTLCache(default_ttl_sec=10.0, max_size=2)
        cache.set("x", 1)
        cache.set("y", 2)
        cache.set("z", 3)  # Should evict oldest
        self.assertEqual(cache.size(), 2)

if __name__ == "__main__":
    unittest.main()
