# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function


class APIError(Exception):
    def __init__(self, exc, *args):
        super(APIError, self).__init__(*args)
        self.response = exc.response
        self.request = exc.request


class APIStatusError(APIError):
    def __init__(self, exc, *args):
        super(APIStatusError, self).__init__(exc, *args)
        self.status_code = self.response.status_code


class APIRequestError(APIError):
    pass


class TokenExpiredError(Exception):
    pass


class TimeoutError(Exception):
    pass
