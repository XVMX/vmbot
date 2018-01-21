# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import os
import StringIO
import logging

import requests

from vmbot.helpers.files import BOT_DB
from vmbot.helpers.exceptions import APIError, APIStatusError, APIRequestError, NoCacheError
import vmbot.helpers.database as db

from vmbot.helpers import api


def flawed_response(*args, **kwargs):
    """Return a requests.Response with 404 status code."""
    res = requests.Response()
    res.status_code = 404
    res._content = b"ASCII text"
    res.encoding = "ascii"
    return res


def esi_warning_response(*args, **kwargs):
    """Return a requests.Response with a deprecation warning header."""
    res = requests.Response()
    res.status_code = 200
    res.headers['warning'] = "299 - This endpoint is deprecated."
    res._content = b'{"res": true}'
    res.encoding = "ascii"
    return res


class TestAPI(unittest.TestCase):
    zbot_regex = ("Joker Gates [XVMX] <CONDI> | Hurricane ([\d,]+ point(s)) | [\d,.]+m ISK | "
                  "Saranen (Lonetrek) | 47 participant(s) (23,723 damage) | "
                  "2016-06-10 02:09:38")

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

    def test_get_db_session(self):
        sess = api._get_db_session()
        self.assertIs(api._get_db_session(), sess)

    def test_get_requests_session(self):
        sess = api._get_requests_session()
        self.assertIs(api._get_requests_session(), sess)

    def test_get_name(self):
        # character_id: 91754106 Joker Gates
        self.assertEqual(api.get_name(91754106), "Joker Gates")

    def test_get_name_invalidid(self):
        self.assertEqual(api.get_name(-1), "{ERROR}")

    def test_get_tickers(self):
        # corp_id: 1164409536 [OTHER]
        # ally_id: 159826257 <OTHER>
        self.assertTupleEqual(api.get_tickers(1164409536, 159826257), ("OTHER", "OTHER"))

    def test_get_tickers_corponly(self):
        # corp_id: 2052404106 [XVMX] (member of <CONDI>)
        self.assertTupleEqual(api.get_tickers(2052404106, None), ("XVMX", "CONDI"))

    def test_get_tickers_allianceonly(self):
        # ally_id: 99005065 <HKRAB>
        self.assertTupleEqual(api.get_tickers(None, 99005065), (None, "HKRAB"))

    def test_get_tickers_invalidid(self):
        self.assertTupleEqual(api.get_tickers(-1, -1), ("ERROR", "ERROR"))

    def test_get_tickers_none(self):
        self.assertTupleEqual(api.get_tickers(None, None), (None, None))

    def test_zbot(self):
        self.assertRegexpMatches(api.zbot("54520379"), self.zbot_regex)

    def test_zbot_int(self):
        self.assertRegexpMatches(api.zbot(54520379), self.zbot_regex)

    def test_zbot_invalidid(self):
        self.assertEqual(api.zbot("-2"), "Failed to load data for https://zkillboard.com/kill/-2/")

    @mock.patch("vmbot.helpers.api.request_rest", side_effect=APIError("TestException"))
    def test_zbot_APIError(self, mock_rest):
        self.assertEqual(api.zbot("54520379"), "TestException")

    def test_request_rest(self):
        test_url = "https://httpbin.org/cache/60"

        # Test without cache
        with mock.patch("vmbot.helpers.api.parse_http_cache", side_effect=NoCacheError):
            res_nocache = api.request_rest(test_url)
            self.assertIsInstance(res_nocache, dict)

        # Test with cache
        res_cache = api.request_rest(test_url)
        self.assertIsInstance(res_cache, dict)

        # Test cached response
        self.assertDictEqual(api.request_rest(test_url), res_cache)

    def test_request_esi(self):
        test_route = "/v1/status/"

        # Test without cache
        with mock.patch("vmbot.helpers.api.parse_http_cache", side_effect=NoCacheError):
            res_nocache = api.request_esi(test_route)
            self.assertIsInstance(res_nocache, dict)

        # Test with cache
        res, res_head = api.request_esi(test_route, with_head=True)
        self.assertIsInstance(res, dict)

        # Test cached response
        res_cache, res_cache_head = api.request_esi(test_route, with_head=True)
        self.assertDictEqual(res_cache, res)
        self.assertDictEqual(dict(res_cache_head), dict(res_head))

    @mock.patch("vmbot.helpers.api.request_api", side_effect=esi_warning_response)
    def test_request_esi_warning(self, mock_esi):
        log = StringIO.StringIO()
        handler = logging.StreamHandler(log)
        logger = logging.getLogger("vmbot.helpers.api.esi")
        logger.addHandler(handler)

        self.assertDictEqual(api.request_esi("TestURL"), {'res': True})
        self.assertTrue(log.getvalue().startswith('Route "TestURL" is deprecated'))

        logger.removeHandler(handler)

    @mock.patch("requests.Session.request", side_effect=requests.RequestException("TestException"))
    def test_request_api_RequestException(self, mock_requests):
        self.assertRaisesRegexp(APIRequestError, "Error while connecting to API: TestException",
                                api.request_api, "TestURL")

    @mock.patch("requests.Session.request", side_effect=flawed_response)
    def test_request_api_flawedresponse(self, mock_requests):
        self.assertRaisesRegexp(APIStatusError, "API returned error code 404",
                                api.request_api, "TestURL")


if __name__ == "__main__":
    unittest.main()
