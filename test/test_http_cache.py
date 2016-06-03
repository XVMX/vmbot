import unittest

import os

from vmbot.helpers.files import CACHE_DB

from vmbot.helpers import cache


class TestHTTPCache(unittest.TestCase):
    def tearDown(self):
        self.setUpClass()

    @classmethod
    def setUpClass(cls):
        try:
            os.remove(CACHE_DB)
        except OSError:
            pass

    def test_set_http(self):
        self.assertTrue(cache.set_http("key", doc="value"))

    def test_set_http_overwrite(self):
        self.assertTrue(cache.set_http("key", doc="value"))
        self.assertTrue(cache.set_http("key", doc="other value"))
        self.assertEqual(cache.get_http("key"), "other value")

    def test_get_http(self):
        cache.set_http("key", doc="value")
        self.assertEqual(cache.get_http("key"), "value")

    def test_get_http_expired(self):
        cache.set_http("key", doc="value", expiry=1)
        self.assertIsNone(cache.get_http("key"))

    def test_get_http_notfound(self):
        cache.set_http("key", doc="value")
        self.assertIsNone(cache.get_http("other key"))

    def test_get_http_nodb(self):
        self.assertIsNone(cache.get_http("other key"))

    def test_update(self):
        self.assertTrue(cache.set_http("key", doc="value"))
        cache._CACHE_VERSION += 1
        self.assertTrue(cache.set_http("key", doc="other value"))
        self.assertEqual(cache.get_http("key"), "other value")


if __name__ == "__main__":
    unittest.main()
