# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import mock

from functools import partial

import responses

from . import files

import config


def _noop_cache(sess, *args, **kwargs):
    return sess


def disable_cache():
    return mock.patch("vmbot.helpers.api.CacheControl", new=_noop_cache)


def _add_to_mock(mock, f=None, **kwargs):
    if f is not None:
        kwargs[b"body"] = files.open(f, "rb")

    mock.add(**kwargs)


# Generic responses
add_plain_200 = partial(_add_to_mock, method=responses.GET, status=200, body="Welcome!")
add_plain_404 = partial(_add_to_mock, method=responses.GET, status=404, body="Not Found")

# bash.org is a bit unstable at times and the website never changes, so we keep a local copy
add_bash_org_random_200 = partial(
    _add_to_mock, method=responses.GET, url="http://bash.org/?random",
    status=200, content_type="text/html", f="bash_org_random_200.html"
)

# Special case responses for xkcd
add_xkcd_info_200 = partial(
    _add_to_mock, method=responses.GET, url="https://xkcd.com/info.0.json",
    status=200, content_type="application/json", f="xkcd_info_0_200.json"
)

# Special case responses for Urban Dictionary
add_ud_define_unk_200 = partial(
    _add_to_mock, method=responses.GET, url="https://api.urbandictionary.com/v0/define",
    status=200, content_type="application/json;charset=utf-8", f="ud_define_unk_200.json"
)
add_ud_define_api_200 = partial(
    _add_to_mock, method=responses.GET, url="https://api.urbandictionary.com/v0/define",
    status=200, content_type="application/json;charset=utf-8", f="ud_define_api_200.json"
)

# Imgur API requires authentication with client ID
_IMGUR_AUTH = "Client-ID {}".format(config.IMGUR_ID)
add_imgur_viral_200 = partial(
    _add_to_mock, method=responses.GET, url="https://api.imgur.com/3/gallery/hot/viral",
    status=200, content_type="application/json", f="imgur_viral_200.json",
    match=[responses.matchers.header_matcher({'Authorization': _IMGUR_AUTH})]
)
add_imgur_search_corgi_200 = partial(
    _add_to_mock, method=responses.GET, url="https://api.imgur.com/3/gallery/search/viral",
    status=200, content_type="application/json", f="imgur_search_corgi_200.json",
    match=[responses.matchers.header_matcher({'Authorization': _IMGUR_AUTH})]
)
add_imgur_search_empty_200 = partial(
    _add_to_mock, method=responses.GET, url="https://api.imgur.com/3/gallery/search/viral",
    status=200, content_type="application/json", f="imgur_search_empty_200.json",
    match=[responses.matchers.header_matcher({'Authorization': _IMGUR_AUTH})]
)
