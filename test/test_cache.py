# coding: utf-8

import unittest

from datetime import datetime, timedelta
import os
import xml.etree.ElementTree as ET

from vmbot.helpers.files import BOT_DB
from vmbot.helpers.exceptions import NoCacheError
import vmbot.helpers.database as db

from vmbot.models.cache import parse_cache_control, parse_xml_cache, HTTPCacheObject


class TestCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            os.remove(BOT_DB)
        except OSError:
            pass
        else:
            db.init_db()

    def setUp(self):
        self.sess = db.Session()

    def tearDown(self):
        self.sess.close()
        self.setUpClass()

    def test_parse_cache_control(self):
        self.assertIsInstance(parse_cache_control("max-age=60"), datetime)

    def test_parse_cache_control_empty(self):
        self.assertRaises(NoCacheError, parse_cache_control, "")

    def test_parse_cache_control_nocache(self):
        self.assertRaises(NoCacheError, parse_cache_control, "no-cache")

    def test_parse_xml_cache(self):
        api_sample = """<?xml version='1.0' encoding='UTF-8'?>
                        <eveapi version="2">
                          <currentTime>2016-09-05 16:56:32</currentTime>
                          <result>
                            <serverOpen>True</serverOpen>
                            <onlinePlayers>28084</onlinePlayers>
                          </result>
                          <cachedUntil>2016-09-05 16:58:19</cachedUntil>
                        </eveapi>"""
        self.assertIsInstance(parse_xml_cache(ET.fromstring(api_sample)), datetime)

    def test_parse_xml_cache_nocache(self):
        self.assertRaises(NoCacheError, parse_xml_cache, ET.fromstring("<empty />"))

    def test_basic(self):
        HTTPCacheObject("abc", b"123").save(self.sess)
        self.assertEqual(HTTPCacheObject.get("abc", self.sess), b"123")

    def test_overwrite(self):
        HTTPCacheObject("abc", b"123").save(self.sess)
        HTTPCacheObject("abc", b"789").save(self.sess)
        self.assertEqual(HTTPCacheObject.get("abc", self.sess), b"789")

    def test_expired(self):
        HTTPCacheObject("abc", b"123",
                        expiry=datetime.utcnow() - timedelta(hours=1)).save(self.sess)
        self.assertIsNone(HTTPCacheObject.get("abc", self.sess))

    def test_get_http_notfound(self):
        self.assertIsNone(HTTPCacheObject.get("abc", self.sess))


if __name__ == "__main__":
    unittest.main()
