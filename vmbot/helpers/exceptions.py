# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function


class NoCacheError(Exception):
    pass


class APIError(Exception):
    pass


class APIStatusError(APIError):
    pass


class APIRequestError(APIError):
    pass


class TokenExpiredError(Exception):
    pass


class TimeoutError(Exception):
    pass
