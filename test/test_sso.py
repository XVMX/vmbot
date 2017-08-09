# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

import requests

from vmbot.helpers.exceptions import TokenExpiredError

from vmbot.helpers.sso import SSOToken


GRANT_RES = {'access_token': "abc123", 'token_type': "test",
             'expires_in': 1200, 'refresh_token': "xyz789"}
VERIFY_RES = {'Scopes': " "}


class TestSSOToken(unittest.TestCase):
    @mock.patch("vmbot.helpers.sso.SSOToken.request_crest", return_value=VERIFY_RES)
    def setUp(self, mock_crest):
        self.token = SSOToken("test_token", "test", 1200, "test_refresh_token")

    def tearDown(self):
        del self.token

    @mock.patch("vmbot.helpers.api.request_api", return_value=requests.Response())
    @mock.patch("requests.Response.json", return_value=GRANT_RES)
    @mock.patch("vmbot.helpers.sso.SSOToken.request_crest", return_value=VERIFY_RES)
    def test_factories(self, mock_crest, mock_json, mock_api):
        self.assertIsInstance(SSOToken.from_authorization_code("abc123"), SSOToken)
        self.assertIsInstance(SSOToken.from_refresh_token("xyz789"), SSOToken)

    @mock.patch("vmbot.helpers.sso.SSOToken._request_grant", return_value=GRANT_RES)
    def test_token_update(self, mock_grant):
        self.token._expiry = datetime.utcnow() - timedelta(hours=1)
        self.assertEqual(self.token.access_token, "abc123")

    def test_token_update_invalid(self):
        self.token._refresh_token = None
        self.token._expiry = datetime.utcnow() - timedelta(hours=1)
        with self.assertRaises(TokenExpiredError):
            self.token.access_token

    @mock.patch("vmbot.helpers.api.request_rest", return_value={'res': True})
    @mock.patch("vmbot.helpers.api.request_xml", return_value=ET.Element("res"))
    def test_token_request(self, mock_xml, mock_rest):
        self.assertDictEqual(self.token.request_crest("TestURL"), {'res': True})
        self.assertIsInstance(self.token.request_xml("TestURL"), ET.Element)

    def test_request_grant_invalid(self):
        self.assertRaises(NotImplementedError, SSOToken._request_grant, "abc123", "token")


if __name__ == "__main__":
    unittest.main()
