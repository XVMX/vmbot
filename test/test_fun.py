# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

import shutil
import re

import responses
from bs4 import BeautifulSoup

from .support.xmpp import mock_muc_mess
from .support import api as api_support
from .support import files as files_support
from vmbot.helpers.files import EMOTES, HTTPCACHE
from vmbot.helpers import api

from vmbot.fun import Fun


@api_support.disable_cache()
class TestFun(unittest.TestCase):
    default_mess = mock_muc_mess(b"")
    default_args = ""
    rating_regex = r"(?:\+|-)(?:\d+,)*\d+"

    @classmethod
    def tearDownClass(cls):
        # Reset _API_REG to re-enable caching
        api._API_REG = api.threading.local()

    def setUp(self):
        self.fun = Fun()

    def tearDown(self):
        del self.fun

    def test_rtd(self):
        with open(EMOTES, "rU") as emotes_file:
            emotes = emotes_file.read()

        self.assertIn(self.fun.rtd(self.default_mess, self.default_args), emotes)

    @responses.activate
    def test_rtq(self):
        api_support.add_bash_org_random_200(responses)
        res = self.fun.rtq(self.default_mess, self.default_args)

        try:
            quote_href = re.search(r"http://bash\.org/(\?\d+)", res).group(1)
        except AttributeError:
            self.fail("rtq didn't return an http://bash.org link in test_rtq")

        with files_support.open("bash_org_random_200.html", 'r') as f:
            soup = BeautifulSoup(f, "html.parser")

        if soup.find("a", href=quote_href) is None:
            self.fail("Failed to find quote {} in test_rtq".format(quote_href))

        self.assertRegexpMatches(res, r"^http://bash\.org/\?\d+ \({}\)\n".format(self.rating_regex))

    @responses.activate
    def test_rtq_APIError(self):
        api_support.add_plain_404(responses, url="http://bash.org/?random")
        self.assertEqual(self.fun.rtq(self.default_mess, self.default_args),
                         "API returned error code 404")

    @responses.activate
    def test_rtq_unexpected(self):
        api_support.add_plain_200(responses, url="http://bash.org/?random")
        self.assertEqual(self.fun.rtq(self.default_mess, self.default_args),
                         "Failed to load any quotes from http://bash.org/?random")

    def test_rtxkcd(self):
        res = self.fun.rtxkcd(self.default_mess, self.default_args)

        if re.search(r"https://xkcd\.com/\d+/", res) is None:
            self.fail("rtxkcd didn't return an https://xkcd.com link in test_rtxkcd")

        self.assertRegexpMatches(res, r'^<a href=".+">.+</a> \(<em>\d{1,4}(?:/\d{1,2}){2}</em>\)$')

    def test_rtxkcd_APIError(self):
        # Exception on first request
        with responses.RequestsMock() as rsps:
            api_support.add_plain_404(rsps, url="https://xkcd.com/info.0.json")
            self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args),
                             "API returned error code 404")

        # Exception on second request
        with responses.RequestsMock() as rsps:
            api_support.add_xkcd_info_200(rsps)
            api_support.add_plain_404(rsps, url=re.compile(r"https://xkcd.com/\d+/info.0.json"))
            self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args),
                             "API returned error code 404")

    def test_rtxkcd_unexpected(self):
        # Non-JSON response to first request
        with responses.RequestsMock() as rsps:
            api_support.add_plain_200(rsps, url="https://xkcd.com/info.0.json")
            self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args),
                             "Error while parsing response")

        # Non-JSON response to second request
        with responses.RequestsMock() as rsps:
            api_support.add_xkcd_info_200(rsps)
            api_support.add_plain_200(rsps, url=re.compile(r"https://xkcd.com/\d+/info.0.json"))
            self.assertRegexpMatches(self.fun.rtxkcd(self.default_mess, self.default_args),
                                     r"^Failed to load xkcd #\d+ from ")

    @responses.activate
    def test_urban(self):
        api_support.add_ud_define_api_200(responses)
        self.assertRegexpMatches(self.fun.urban(self.default_mess, "API"),
                                 (r'^<a href=".+?">.+?</a> by <em>.+?</em> '
                                  r"rated {}<br />").format(self.rating_regex))

    def test_urban_random(self):
        self.assertRegexpMatches(self.fun.rtud(self.default_mess, self.default_args),
                                 (r'^<a href=".+?">.+?</a> by <em>.+?</em> '
                                  r"rated {}<br />").format(self.rating_regex))

    def test_urban_link(self):
        match = re.search("(.+)", "API")  # hack to create a suitable MatchObject
        self.assertEqual(self.fun.urban_link(match),
                         '<a href="https://www.urbandictionary.com/define.php?term=API">API</a>')

    @responses.activate
    def test_urban_unk(self):
        api_support.add_ud_define_unk_200(responses)
        self.assertEqual(self.fun.urban(self.default_mess, "API"),
                         'Failed to find any definitions for "API"')

    @responses.activate
    def test_urban_APIError(self):
        api_support.add_plain_404(responses, url="https://api.urbandictionary.com/v0/define")
        self.assertEqual(self.fun.urban(self.default_mess, "API"),
                         "API returned error code 404")

    @responses.activate
    def test_urban_unexpected(self):
        api_support.add_plain_200(responses, url="https://api.urbandictionary.com/v0/define")
        self.assertEqual(self.fun.urban(self.default_mess, "API"), "Error while parsing response")

    @responses.activate
    def test_imgur(self):
        api_support.add_imgur_search_corgi_200(responses)
        self.assertRegexpMatches(self.fun.corgitax(self.default_mess, self.default_args),
                                 r'^<a href=".+">.+</a> \({}\)$'.format(self.rating_regex))

    @responses.activate
    def test_imgur_random(self):
        api_support.add_imgur_viral_200(responses)
        self.assertRegexpMatches(self.fun.imgur(self.default_mess, self.default_args),
                                 r'^<a href=".+">.+</a> \({}\)$'.format(self.rating_regex))

    @responses.activate
    def test_imgur_empty(self):
        api_support.add_imgur_search_empty_200(responses)
        self.assertEqual(self.fun.imgur(self.default_mess, "e94iwps0mfks3"),
                         'Failed to find any images for "e94iwps0mfks3"')

    @responses.activate
    def test_imgur_APIError(self):
        api_support.add_plain_404(responses, url="https://api.imgur.com/3/gallery/hot/viral")
        self.assertEqual(self.fun.imgur(self.default_mess, self.default_args),
                         "API returned error code 404")

    @responses.activate
    def test_imgur_unexpected(self):
        api_support.add_plain_200(responses, url="https://api.imgur.com/3/gallery/hot/viral")
        self.assertEqual(self.fun.imgur(self.default_mess, self.default_args),
                         "Error while parsing response")


if __name__ == "__main__":
    unittest.main()
