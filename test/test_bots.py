# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import shutil

import requests

from vmbot.helpers.files import HTTPCACHE
from vmbot.helpers.exceptions import APIError, APIStatusError
from vmbot.helpers import api

from vmbot.helpers import bots


class TestBots(unittest.TestCase):
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

    def test_zbot(self):
        # See https://zkillboard.com/kill/54520379/
        self.assertRegexpMatches(bots.zbot("54520379"), self.zbot_regex)

    def test_zbot_int(self):
        self.assertRegexpMatches(bots.zbot(54520379), self.zbot_regex)

    def test_zbot_invalidid(self):
        self.assertEqual(bots.zbot("-2"), "Failed to load data for https://zkillboard.com/kill/-2/")

    @mock.patch("vmbot.helpers.api.request_api",
                side_effect=APIError(requests.RequestException(), "TestException"))
    def test_zbot_APIError_zkb(self, mock_api):
        self.assertEqual(bots.zbot("54520379"), "TestException")

    @mock.patch("vmbot.helpers.api.request_esi",
                side_effect=APIError(requests.RequestException(), "TestException"))
    def test_zbot_APIError_esi(self, mock_esi):
        self.assertEqual(bots.zbot("54520379"), "TestException")

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
        self.assertEqual(bots.ytbot("GNFgkN1kbNc"),
                         "Some stream | LIVE | ABCDEF | 1,963 views | 2019-01-08 22:16:44")

        # Upcoming stream
        mock_api.return_value._content = (
            b'{"items":[{"snippet":{"publishedAt":"2018-10-29T10:18:23Z",'
            b'"channelTitle": "ABCDEF","liveBroadcastContent":"upcoming",'
            b'"localized":{"title":"Some future stream"}},"contentDetails":{"duration":"PT0S",'
            b'"definition": "sd"},"statistics":{"viewCount": "84"}}]}'
        )
        self.assertEqual(bots.ytbot("GNFgkN1kbNc"),
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
            bots.ytbot("GNFgkN1kbNc"),
            "Some video | HD | ABCDEF | 0:00:22 | 784,301 views | "
            "98.39% likes (+98,437/-1,613) | 2019-01-01 03:52:19"
        )

    @mock.patch("config.YT_KEY", new=None)
    def test_ytbot_nokey(self):
        self.assertFalse(bots.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api", return_value=requests.Response())
    def test_ytbot_noitems(self, mock_api):
        mock_api.return_value.status_code = 200
        mock_api.return_value._content = b'{"items":[]}'
        mock_api.return_value.encoding = "utf-8"

        self.assertIsNone(bots.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api")
    def test_ytbot_quotaExceeded(self, mock_api):
        resp = requests.Response()
        resp.status_code = 403
        resp._content = b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}'
        resp.encoding = "utf-8"

        mock_api.side_effect = APIStatusError(requests.RequestException(response=resp),
                                              "TestException")
        self.assertFalse(bots.ytbot("GNFgkN1kbNc"))

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api")
    def test_ytbot_404(self, mock_api):
        resp = requests.Response()
        resp.status_code = 404
        resp._content = b'{"error":{"errors":[{"reason":"videoNotFound"}]}}'
        resp.encoding = "utf-8"

        mock_api.side_effect = APIStatusError(requests.RequestException(response=resp),
                                              "TestException")
        self.assertIsNone(bots.ytbot("GNFgkN1kbNc"))

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
        self.assertEqual(bots.ytbot("GNFgkN1kbNc"),
                         "TestException: The request is missing a required parameter.")

    @mock.patch("config.YT_KEY", new="TestKey")
    @mock.patch("vmbot.helpers.api.request_api",
                side_effect=APIError(requests.RequestException(), "TestException"))
    def test_ytbot_APIError(self, mock_api):
        self.assertEqual(bots.ytbot("GNFgkN1kbNc"), "TestException")


if __name__ == '__main__':
    unittest.main()
