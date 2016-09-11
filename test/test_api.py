# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import os
import xml.etree.ElementTree as ET

import requests

from vmbot.helpers.files import BOT_DB
from vmbot.helpers.exceptions import APIError, NoCacheError
import vmbot.helpers.database as db

from vmbot.helpers import api


def flawed_response(*args, **kwargs):
    """Return a requests.Response with 404 status code."""
    res = requests.Response()
    res.status_code = 404
    res._content = b"ASCII text"
    res.encoding = "ascii"
    return res


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            os.remove(BOT_DB)
        except OSError:
            pass
        else:
            db.init_db()

    @classmethod
    def tearDownClass(cls):
        return cls.setUpClass()

    def test_get_tickers(self):
        # corporationID: 1164409536 [OTHER]
        # allianceID: 159826257 <OTHER>
        self.assertTupleEqual(api.get_tickers(1164409536, 159826257), ("OTHER", "OTHER"))

    def test_get_tickers_corponly(self):
        # corporationID: 2052404106 [XVMX] (member of <CONDI>)
        self.assertTupleEqual(api.get_tickers(2052404106, None), ("XVMX", "CONDI"))

    def test_get_tickers_allianceonly(self):
        # allianceID: 99005065 <HKRAB>
        self.assertTupleEqual(api.get_tickers(None, 99005065), (None, "HKRAB"))

    def test_get_tickers_invalidid(self):
        self.assertTupleEqual(api.get_tickers(-1, -1), ("ERROR", "ERROR"))

    def test_get_tickers_none(self):
        self.assertTupleEqual(api.get_tickers(None, None), (None, None))

    def test_get_rest_endpoint(self):
        test_url = "https://crest-tq.eveonline.com/"

        # Test without cache
        with mock.patch("vmbot.helpers.api.parse_cache_control", side_effect=NoCacheError):
            res_nocache = api.get_rest_endpoint(test_url)
            self.assertIsInstance(res_nocache, dict)

        # Test with cache
        res_cache = api.get_rest_endpoint(test_url)
        self.assertIsInstance(res_cache, dict)

        # Test cached response
        self.assertDictEqual(api.get_rest_endpoint(test_url), res_cache)

    def test_post_xml_endpoint(self):
        test_url = "https://api.eveonline.com/server/ServerStatus.xml.aspx"

        # Test without cache
        with mock.patch("vmbot.helpers.api.parse_xml_cache", side_effect=NoCacheError):
            res_nocache = api.post_xml_endpoint(test_url)
            self.assertIsInstance(res_nocache, ET.Element)

        # Test with cache
        res_cache = api.post_xml_endpoint(test_url)
        self.assertIsInstance(res_cache, ET.Element)

        # Test cached response
        self.assertEqual(ET.tostring(api.post_xml_endpoint(test_url)), ET.tostring(res_cache))

    @mock.patch("requests.request",
                side_effect=requests.exceptions.RequestException("TestException"))
    def test_request_api_RequestException(self, mock_requests):
        self.assertRaisesRegexp(APIError, "Error while connecting to API: TestException",
                                api.request_api, "TestURL")

    @mock.patch("requests.request", side_effect=flawed_response)
    def test_request_api_flawedresponse(self, mock_requests):
        self.assertRaisesRegexp(APIError, "API returned error code 404",
                                api.request_api, "TestURL")


if __name__ == "__main__":
    unittest.main()
