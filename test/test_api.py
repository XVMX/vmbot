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
                  r"Saranen (Lonetrek) | 47 attacker(s) (23,723 damage) | "
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
        self.assertIn("XVMX-VMBot", sess.headers['User-Agent'])

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
        # corp_id: 667531913 [GEWNS] (member of <CONDI>)
        self.assertTupleEqual(api.get_tickers(667531913, None), ("GEWNS", "CONDI"))

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

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api", return_value=requests.Response())
    def test_ytbot(self, mock_api):
        mock_api.return_value.status_code = 200
        mock_api.return_value.encoding = "utf-8"

        # Live stream
        mock_api.return_value._content = (
            b'{"items":[{"snippet":{"publishedAt":"2019-01-08T22:16:44Z",'
            b'"channelTitle": "ABCDEF","liveBroadcastContent":"live",'
            b'"localized":{"title":"Some stream"}},"contentDetails":{"duration":"PT0S",'
            b'"definition": "sd"},"statistics":{"viewCount": "1963"}}]}'
        )
        self.assertEqual(api.ytbot("GNFgkN1kbNc"),
                         "Some stream | LIVE | ABCDEF | 1,963 views | 2019-01-08 22:16:44")

        # Upcoming stream
        mock_api.return_value._content = (
            b'{"items":[{"snippet":{"publishedAt":"2018-10-29T10:18:23Z",'
            b'"channelTitle": "ABCDEF","liveBroadcastContent":"upcoming",'
            b'"localized":{"title":"Some future stream"}},"contentDetails":{"duration":"PT0S",'
            b'"definition": "sd"},"statistics":{"viewCount": "84"}}]}'
        )
        self.assertEqual(api.ytbot("GNFgkN1kbNc"),
                         "Some future stream | Upcoming | ABCDEF | 84 views | 2018-10-29 10:18:23")

        # Video
        mock_api.return_value._content = (
            b'{"items":[{"snippet":{"publishedAt":"2019-01-01T03:52:19Z",'
            b'"channelTitle": "ABCDEF","liveBroadcastContent":"none",'
            b'"localized":{"title":"Some video"}},"contentDetails":{"duration":"PT22S",'
            b'"definition": "hd"},"statistics":{"viewCount": "784301",'
            b'"likeCount":"98437","dislikeCount":"1613"}}]}'
        )
        self.assertEqual(
            api.ytbot("GNFgkN1kbNc"),
            "Some video | HD | ABCDEF | 0:00:22 | 784,301 views | "
            "98.39% likes (+98,437/-1,613) | 2019-01-01 03:52:19"
        )

    @mock.patch("config.YT_KEY", new=None)
    def test_ytbot_nokey(self):
        self.assertFalse(api.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api", return_value=requests.Response())
    def test_ytbot_noitems(self, mock_api):
        mock_api.return_value.status_code = 200
        mock_api.return_value._content = b'{"items":[]}'
        mock_api.return_value.encoding = "utf-8"

        self.assertIsNone(api.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api")
    def test_ytbot_quotaExceeded(self, mock_api):
        resp = requests.Response()
        resp.status_code = 403
        resp._content = b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}'
        resp.encoding = "utf-8"

        mock_api.side_effect = APIStatusError(requests.RequestException(response=resp),
                                              "TestException")
        self.assertFalse(api.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api")
    def test_ytbot_404(self, mock_api):
        resp = requests.Response()
        resp.status_code = 404
        resp._content = b'{"error":{"errors":[{"reason":"videoNotFound"}]}}'
        resp.encoding = "utf-8"

        mock_api.side_effect = APIStatusError(requests.RequestException(response=resp),
                                              "TestException")
        self.assertIsNone(api.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api")
    def test_ytbot_APIStatusError(self, mock_api):
        resp = requests.Response()
        resp.status_code = 400
        resp._content = (b'{"error":{"errors":[{"reason":"missingRequiredParameter"}],'
                         b'"message":"The request is missing a required parameter."}}')
        resp.encoding = "utf-8"

        mock_api.side_effect = APIStatusError(requests.RequestException(response=resp),
                                              "TestException")
        self.assertEqual(api.ytbot("GNFgkN1kbNc"),
                         "TestException: The request is missing a required parameter.")

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api",
                side_effect=APIError(requests.RequestException(), "TestException"))
    def test_ytbot_APIError(self, mock_api):
        self.assertEqual(api.ytbot("GNFgkN1kbNc"), "TestException")

    def test_request_esi(self):
        test_route = "/v2/status/"
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
