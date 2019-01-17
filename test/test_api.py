# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import shutil
import StringIO
import logging

import requests

from vmbot.helpers.files import HTTPCACHE
from vmbot.helpers.exceptions import APIError, APIStatusError, APIRequestError

from vmbot.helpers import api


def flawed_response(*args, **kwargs):
    """Return a requests.Response with 404 status code."""
    res = requests.Response()
    res.status_code = 404
    res._content = b"ASCII text"
    res.encoding = "ascii"
    res.from_cache = False
    return res


def esi_warning_response(*args, **kwargs):
    """Return a requests.Response with a deprecation warning header."""
    res = requests.Response()
    res.status_code = 200
    res.headers['warning'] = "299 - This endpoint is deprecated."
    res._content = b'{"res": true}'
    res.encoding = "ascii"
    res.from_cache = False
    return res


class TestAPI(unittest.TestCase):
    zbot_regex = (r"Joker Gates [XVMX] <CONDI> | Hurricane ([\d,]+ point(s)) | [\d,.]+m ISK | "
                  r"Saranen (Lonetrek) | 47 participant(s) (23,723 damage) | "
                  r"2016-06-10 02:09:38")

    @classmethod
    def setUpClass(cls):
        shutil.rmtree(HTTPCACHE, ignore_errors=True)

    @classmethod
    def tearDownClass(cls):
        # _API_REG may still hold a FileCache
        api._API_REG = api.threading.local()
        shutil.rmtree(HTTPCACHE, ignore_errors=True)

    def test_get_requests_session(self):
        sess = api._get_requests_session()
        self.assertIs(api._get_requests_session(), sess)
        self.assertIn("XVMX VMBot", sess.headers['User-Agent'])

    def test_get_names_single(self):
        # character_id: 91754106 Joker Gates
        self.assertDictEqual(api.get_names(91754106), {91754106: "Joker Gates"})

    def test_get_names_multi(self):
        # character_id: 91754106 Joker Gates
        # corporation_id: 2052404106 Valar Morghulis.
        # alliance_id: 1354830081 Goonswarm Federation
        self.assertDictEqual(api.get_names(91754106, 2052404106, 1354830081),
                             {91754106: "Joker Gates", 2052404106: "Valar Morghulis.",
                              1354830081: "Goonswarm Federation"})

    def test_get_names_invalidid(self):
        # character_id: 91754106 Joker Gates
        self.assertDictEqual(api.get_names(91754106, -1), {91754106: "{ERROR}", -1: "{ERROR}"})

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
        # See https://zkillboard.com/kill/54520379/
        self.assertRegexpMatches(api.zbot("54520379"), self.zbot_regex)

    def test_zbot_int(self):
        self.assertRegexpMatches(api.zbot(54520379), self.zbot_regex)

    def test_zbot_invalidid(self):
        self.assertEqual(api.zbot("-2"), "Failed to load data for https://zkillboard.com/kill/-2/")

    @mock.patch("vmbot.helpers.api.request_api",
                side_effect=APIError(requests.RequestException(), "TestException"))
    def test_zbot_APIError_zkb(self, mock_api):
        self.assertEqual(api.zbot("54520379"), "TestException")

    @mock.patch("vmbot.helpers.api.request_esi",
                side_effect=APIError(requests.RequestException(), "TestException"))
    def test_zbot_APIError_esi(self, mock_esi):
        self.assertEqual(api.zbot("54520379"), "TestException")

    def test_request_esi(self):
        test_route = "/v1/status/"
        test_params = {'datasource': "tranquility"}

        res, head = api.request_esi(test_route, params=test_params, with_head=True)
        cached_res = api.request_esi(test_route, params=test_params)
        self.assertDictEqual(res, cached_res)

    @mock.patch("vmbot.helpers.api.request_api", side_effect=esi_warning_response)
    def test_request_esi_warning(self, mock_api):
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
