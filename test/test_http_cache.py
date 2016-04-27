import unittest

import os

from vmbot.helpers.files import CACHE_DB

from vmbot.helpers import cache


class TestHTTPCache(unittest.TestCase):
    def tearDown(self):
        # Delete cache.db after every test case
        try:
            os.remove(CACHE_DB)
        except:
            pass

    def test_setHTTP(self):
        self.assertTrue(cache.setHTTP("key", doc="value"))

    def test_setHTTP_overwrite(self):
        self.assertTrue(cache.setHTTP("key", doc="value"))
        self.assertTrue(cache.setHTTP("key", doc="other value"))
        self.assertEqual(cache.getHTTP("key"), "other value")

    def test_getHTTP(self):
        cache.setHTTP("key", doc="value")
        self.assertEqual(cache.getHTTP("key"), "value")

    def test_getHTTP_expired(self):
        cache.setHTTP("key", doc="value", expiry=1)
        self.assertIsNone(cache.getHTTP("key"))

    def test_getHTTP_notfound(self):
        cache.setHTTP("key", doc="value")
        self.assertIsNone(cache.getHTTP("other key"))

    def test_getHTTP_nodb(self):
        self.assertIsNone(cache.getHTTP("other key"))

    def test_cacheUpdate(self):
        self.assertTrue(cache.setHTTP("key", doc="value"))
        cache._cache_version += 1
        self.assertTrue(cache.setHTTP("key", doc="other value"))
        self.assertEqual(cache.getHTTP("key"), "other value")


if __name__ == "__main__":
    unittest.main()
