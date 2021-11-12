# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import StringIO
import logging

import responses

from .support import api as api_support
from vmbot.helpers.exceptions import APIStatusError, APIRequestError

from vmbot.helpers import api


@api_support.disable_cache()
class TestAPI(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        # Reset _API_REG to re-enable caching
        api._API_REG = api.threading.local()

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

    zbot_regex = (r"Joker Gates [XVMX] <CONDI> | Hurricane ([\d,]+ point(s)) | [\d,.]+m ISK | "
                  r"Saranen (Lonetrek) | 47 attacker(s) (23,723 damage) | "
                  r"2016-06-10 02:09:38")

    def test_zbot(self):
        # See https://zkillboard.com/kill/54520379/
        self.assertRegexpMatches(api.zbot("54520379"), self.zbot_regex)

    def test_zbot_int(self):
        self.assertRegexpMatches(api.zbot(54520379), self.zbot_regex)

    @responses.activate
    def test_zbot_invalidid(self):
        api_support.add_zkb_invalid_200(responses, url="https://zkillboard.com/api/killID/-2/")
        self.assertEqual(api.zbot("-2"), "Failed to load data for https://zkillboard.com/kill/-2/")

    @responses.activate
    def test_zbot_APIError_zkb(self):
        api_support.add_plain_404(responses, url="https://zkillboard.com/api/killID/54520379/")
        self.assertEqual(api.zbot("54520379"), "API returned error code 404")

    @responses.activate
    def test_zbot_APIError_esi(self):
        responses.add_passthru("https://zkillboard.com/api/")
        api_support.add_plain_404(responses,
                                  url=("https://esi.evetech.net/v1/killmails"
                                       "/54520379/d7eb13ed7f6d7877678f422801cf19a5e7387068/"))
        self.assertEqual(api.zbot("54520379"), "API returned error code 404")

    @mock.patch("config.YT_KEY", new="TestKey")
    @responses.activate
    def test_ytbot(self):
        api_support.add_yt_video_200(responses)
        self.assertEqual(api.ytbot("GNFgkN1kbNc"),
                         "Some video | HD | ABCDEF | 0:00:22 | "
                         "784,301 views | 98,437 likes | 2019-01-01 03:52:19")

    @mock.patch("config.YT_KEY", new="TestKey")
    @responses.activate
    def test_ytbot_live(self):
        api_support.add_yt_live_200(responses)
        self.assertEqual(api.ytbot("GNFgkN1kbNc"),
                         "Some stream | LIVE | ABCDEF | 1,963 views | 2019-01-08 22:16:44")

    @mock.patch("config.YT_KEY", new="TestKey")
    @responses.activate
    def test_ytbot_upcoming(self):
        api_support.add_yt_upcoming_200(responses)
        self.assertEqual(api.ytbot("GNFgkN1kbNc"),
                         "Some future stream | Upcoming | ABCDEF | 84 views | 2018-10-29 10:18:23")

    @mock.patch("config.YT_KEY", new="")
    def test_ytbot_nokey(self):
        self.assertFalse(api.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @responses.activate
    def test_ytbot_empty(self):
        api_support.add_yt_video_empty_200(responses)
        self.assertIsNone(api.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @responses.activate
    def test_ytbot_quotaExceeded(self):
        api_support.add_yt_video_quotaExceeded(responses)
        self.assertFalse(api.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @responses.activate
    def test_ytbot_404(self):
        api_support.add_yt_video_404(responses)
        self.assertIsNone(api.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @responses.activate
    def test_ytbot_APIStatusError(self):
        api_support.add_yt_video_400(responses)
        self.assertEqual(
            api.ytbot("GNFgkN1kbNc"),
            "API returned error code 400: No filter selected. Expected one of: myRating, chart, id"
        )

    @mock.patch("config.YT_KEY", new="TestKey")
    @responses.activate
    def test_ytbot_APIError(self):
        self.assertRegexpMatches(api.ytbot("GNFgkN1kbNc"),
                                 r"^Error while connecting to API: Connection refused")

    def test_request_esi(self):
        res, head = api.request_esi("/v2/status/", params={'datasource': "tranquility"},
                                    with_head=True)
        self.assertTrue('players' in res)

    @responses.activate
    def test_request_esi_warning(self):
        api_support.add_esi_status_warning_200(responses)

        log = StringIO.StringIO()
        handler = logging.StreamHandler(log)
        logger = logging.getLogger("vmbot.helpers.api.esi")
        logger.addHandler(handler)

        api.request_esi("/v2/status/")
        self.assertTrue(log.getvalue().startswith('Route "/v2/status/" is deprecated\n'))

        logger.removeHandler(handler)

    @responses.activate
    def test_request_api_RequestException(self):
        self.assertRaisesRegexp(APIRequestError,
                                r"^Error while connecting to API: Connection refused",
                                api.request_api, "https://httpbin.org/get")

    def test_request_api_HTTPError(self):
        self.assertRaisesRegexp(APIStatusError, r"^API returned error code 404$",
                                api.request_api, "https://httpbin.org/status/404")


if __name__ == "__main__":
    unittest.main()
