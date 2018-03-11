# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime, timedelta

import requests

from vmbot.helpers.exceptions import NoCacheError
import vmbot.helpers.database as db

from vmbot.models.cache import parse_http_cache, HTTPCacheObject, ESICacheObject


class TestCache(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        db.Session.configure(bind=db.engine)

    def setUp(self):
        self.db_engine = db.create_engine("sqlite://")
        db.init_db(self.db_engine)
        db.Session.configure(bind=self.db_engine)
        self.sess = db.Session()

    def tearDown(self):
        self.sess.close()
        self.db_engine.dispose()
        del self.db_engine

    def test_parse_http_cache(self):
        self.assertIsInstance(parse_http_cache({'Cache-Control': "max-age=60"}), datetime)

    def test_parse_http_cache_expires(self):
        self.assertIsInstance(parse_http_cache(
            {'Cache-Control': "public",
             'Expires': "Thu, 01 Dec 2020 16:00:00 GMT"}
            ), datetime
        )

    def test_parse_http_cache_empty(self):
        self.assertRaises(NoCacheError, parse_http_cache, {})

    def test_parse_http_cache_nocache(self):
        self.assertRaises(NoCacheError, parse_http_cache, {'Cache-Control': "no-cache"})

    def test_parse_http_cache_notime(self):
        self.assertRaises(NoCacheError, parse_http_cache, {'Cache-Control': ""})

    def test_basic(self):
        HTTPCacheObject("abc", b"123").save(self.sess)
        self.assertEqual(HTTPCacheObject.get(self.sess, "abc"), b"123")

    def test_overwrite(self):
        HTTPCacheObject("abc", b"123").save(self.sess)
        HTTPCacheObject("abc", b"789").save(self.sess)
        self.assertEqual(HTTPCacheObject.get(self.sess, "abc"), b"789")

    def test_expired(self):
        HTTPCacheObject("abc", b"123",
                        expiry=datetime.utcnow() - timedelta(hours=1)).save(self.sess)
        self.assertIsNone(HTTPCacheObject.get(self.sess, "abc"))

    def test_get_http_notfound(self):
        self.assertIsNone(HTTPCacheObject.get(self.sess, "abc"))

    def test_esi(self):
        r = requests.Response()
        r._content = b"123"
        ESICacheObject("abc", r).save(self.sess)

        r = ESICacheObject.get(self.sess, "abc")
        self.assertEqual(r.content, b"123")
        self.assertDictEqual(dict(r.headers), {})

    def test_get_esi_notfound(self):
        self.assertIsNone(ESICacheObject.get(self.sess, "abc"))


if __name__ == "__main__":
    unittest.main()
