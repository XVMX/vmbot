# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from datetime import datetime, timedelta

import requests

from vmbot.helpers.exceptions import TokenExpiredError

from vmbot.helpers.sso import SSOToken


# JWT: {}.{'scp': [], 'sub': "CHARACTER:EVE:123456"}.
JWT_RES = "e30=.eyJzY3AiOiBbXSwgInN1YiI6ICJDSEFSQUNURVI6RVZFOjEyMzQ1NiJ9."
GRANT_RES = {'access_token': JWT_RES, 'token_type': "test",
             'expires_in': 1200, 'refresh_token': "xyz789"}


class TestSSOToken(unittest.TestCase):
    def setUp(self):
        self.token = SSOToken(**GRANT_RES)

    def tearDown(self):
        del self.token

    @mock.patch("vmbot.helpers.api.request_api", return_value=requests.Response())
    @mock.patch("requests.Response.json", return_value=GRANT_RES)
    def test_factories(self, mock_json, mock_api):
        self.assertIsInstance(SSOToken.from_authorization_code("abc123"), SSOToken)
        self.assertIsInstance(SSOToken.from_refresh_token("xyz789"), SSOToken)

    @mock.patch("vmbot.helpers.sso.SSOToken._request_grant", return_value=GRANT_RES)
    def test_token_update(self, mock_grant):
        self.token._expiry = datetime.utcnow() - timedelta(hours=1)
        self.assertEqual(self.token.auth, "test " + JWT_RES)

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
