# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from datetime import datetime, timedelta

import requests

from vmbot.helpers.exceptions import TokenExpiredError

from vmbot.helpers.sso import SSOToken


GRANT_RES = {'access_token': "abc123", 'token_type': "test",
             'expires_in': 1200, 'refresh_token': "xyz789"}
VERIFY_RES = {'Scopes': " ", 'CharacterID': 123456}


class TestSSOToken(unittest.TestCase):
    @mock.patch("vmbot.helpers.sso.SSOToken.request_esi", return_value=VERIFY_RES)
    def setUp(self, mock_esi):
        self.token = SSOToken("test_token", "test", 1200, "test_refresh_token")

    def tearDown(self):
        del self.token

    @mock.patch("vmbot.helpers.api.request_api", return_value=requests.Response())
    @mock.patch("requests.Response.json", return_value=GRANT_RES)
    @mock.patch("vmbot.helpers.sso.SSOToken.request_esi", return_value=VERIFY_RES)
    def test_factories(self, mock_esi, mock_json, mock_api):
        self.assertIsInstance(SSOToken.from_authorization_code("abc123"), SSOToken)
        self.assertIsInstance(SSOToken.from_refresh_token("xyz789"), SSOToken)

    @mock.patch("vmbot.helpers.sso.SSOToken._request_grant", return_value=GRANT_RES)
    def test_token_update(self, mock_grant):
        self.token._expiry = datetime.utcnow() - timedelta(hours=1)
        self.assertEqual(self.token.auth, "test abc123")

    def test_token_update_invalid(self):
        self.token._refresh_token = None
        self.token._expiry = datetime.utcnow() - timedelta(hours=1)
        with self.assertRaises(TokenExpiredError):
            self.token.auth()

    @mock.patch("vmbot.helpers.api.request_esi", return_value={'res': True})
    def test_token_request_esi(self, mock_esi):
        self.assertDictEqual(self.token.request_esi("TestURL"), {'res': True})

    def test_request_grant_invalid(self):
        self.assertRaises(NotImplementedError, SSOToken._request_grant, "abc123", "token")


if __name__ == "__main__":
    unittest.main()
