# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta
import base64

from .exceptions import TokenExpiredError
from . import api

import config

_SSO_B64 = base64.b64encode(config.SSO['client_id'] + ':' + config.SSO['client_secret'])


class SSOToken(object):
    """Store and manage an EVE Online SSO token."""

    def __init__(self, access_token, token_type, expires_in, refresh_token=None):
        self._access_token = access_token
        self._type = token_type
        self._expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        self._refresh_token = refresh_token

        # See https://github.com/ccpgames/esi-issues/issues/198#issuecomment-318818318
        res = self.request_esi("/verify/")
        self.scopes = res['Scopes'].split()

    @classmethod
    def from_authorization_code(cls, code):
        return cls(**cls._request_grant(code, type_="authorization_code"))

    @classmethod
    def from_refresh_token(cls, refresh_token):
        return cls(**cls._request_grant(refresh_token, type_="refresh_token"))

    @property
    def access_token(self):
        if self._expiry < datetime.utcnow():
            self.update_token()

        return self._access_token

    def update_token(self):
        """Refresh access token using refresh token if available."""
        if self._refresh_token is None:
            raise TokenExpiredError

        res = self._request_grant(self._refresh_token, "refresh_token")
        self._access_token = res['access_token']
        self._type = res['token_type']
        self._expiry = datetime.utcnow() + timedelta(seconds=res['expires_in'])

    def request_esi(self, route, fmt=(), params=None, headers=None, timeout=3, method="GET"):
        if headers is None:
            headers = {}
        headers['Authorization'] = self._type + ' ' + self.access_token
        return api.request_esi(route, fmt, params, headers, timeout, method)

    def request_crest(self, url, params=None, timeout=3, method="GET"):
        headers = {'Authorization': self._type + ' ' + self.access_token}
        return api.request_rest(url, params, headers, timeout, method)

    def request_xml(self, url, params=None, timeout=3, method="POST"):
        # Docs: https://community.eveonline.com/news/patch-notes/patch-notes-for-eve-online-citadel
        if params is None:
            params = {}
        params['accessToken'] = self.access_token
        return api.request_xml(url, params, None, timeout, method)

    @staticmethod
    def _request_grant(token, type_="authorization_code"):
        url = config.SSO['base_url'] + "/oauth/token"
        headers = {'Authorization': "Basic " + _SSO_B64}
        payload = {'grant_type': type_}
        if type_ == "authorization_code":
            payload['code'] = token
        elif type_ == "refresh_token":
            payload['refresh_token'] = token
        else:
            raise NotImplementedError

        return api.request_api(url, params=payload, headers=headers, method="POST").json()
