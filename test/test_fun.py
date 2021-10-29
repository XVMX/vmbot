# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import shutil
import re

import requests
from bs4 import BeautifulSoup

from .test_api import flawed_response
from vmbot.helpers.files import EMOTES, HTTPCACHE
from vmbot.helpers.exceptions import APIError
from vmbot.helpers import api

from vmbot.fun import Fun


class TestFun(unittest.TestCase):
    default_mess = ""
    default_args = ""

    @classmethod
    def setUpClass(cls):
        shutil.rmtree(HTTPCACHE, ignore_errors=True)

    @classmethod
    def tearDownClass(cls):
        # _API_REG may still hold a FileCache
        api._API_REG = api.threading.local()
        shutil.rmtree(HTTPCACHE, ignore_errors=True)

    def setUp(self):
        self.fun = Fun()

    def tearDown(self):
        del self.fun

    def test_rtd(self):
        with open(EMOTES, "rU") as emotes_file:
            emotes = emotes_file.read()

        self.assertIn(self.fun.rtd(self.default_mess, self.default_args), emotes)

    def test_rtq(self):
        res = self.fun.rtq(self.default_mess, self.default_args)

        try:
            quote_url = re.search(r"http://bash\.org/\?\d+", res).group(0)
        except AttributeError:
            self.fail("rtq didn't return an http://bash.org link in test_rtq")

        try:
            r = requests.get(quote_url, timeout=5)
        except requests.RequestException as e:
            self.skipTest("Error while connecting to http://bash.org in test_rtq: {}".format(e))
        soup = BeautifulSoup(r.text, "html.parser")

        try:
            quote = soup.find("p", class_="quote")
            quote_rating = int(quote.find("font").text)
            quote = quote.next_sibling.text
        except AttributeError:
            self.skipTest("Failed to load quote from {} in test_rtq".format(quote_url))

        self.assertEqual(res, "{} ({:+})\n{}".format(quote_url, quote_rating, quote))

    @mock.patch("vmbot.helpers.api.request_api",
                side_effect=APIError(requests.RequestException(), "TestException"))
    def test_rtq_APIError(self, mock_api):
        self.assertEqual(self.fun.rtq(self.default_mess, self.default_args), "TestException")

    @mock.patch("vmbot.helpers.api.request_api", side_effect=flawed_response)
    def test_rtq_flawedresponse(self, mock_api):
        self.assertEqual(self.fun.rtq(self.default_mess, self.default_args),
                         "Failed to load any quotes from http://bash.org/?random")

    def test_rtxkcd(self):
        res = self.fun.rtxkcd(self.default_mess, self.default_args)

        try:
            comic_url = re.search(r"https://xkcd\.com/\d+/", res).group(0)
        except AttributeError:
            self.fail("rtxkcd didn't return an https://xkcd.com link in test_rtxkcd")

        try:
            comic = requests.get(comic_url + "info.0.json", timeout=5).json()
        except requests.RequestException as e:
            self.skipTest("Error while connecting to https://xkcd.com in test_rtxkcd: {}".format(e))
        except ValueError:
            self.skipTest("Failed to load xkcd from {} in test_rtxkcd".format(comic_url))

        self.assertEqual(res, '<a href="{}">{}</a> (<em>{}/{}/{}</em>)'.format(
            comic_url, comic['safe_title'], comic['year'], comic['month'], comic['day']
        ))

    def test_rtxkcd_APIError(self):
        def side_effect(*args, **kwargs):
            """Emulate call and restart patcher to use default side_effect for second request."""
            api_patcher.stop()
            try:
                r = requests.get(*args, **kwargs)
            except requests.RequestException as e:
                self.skipTest(
                    "Error while emulating request in test_rtxkcd_RequestException: {}".format(e)
                )
            api_patcher.start()
            return r

        # Exception at first request
        api_patcher = mock.patch("vmbot.helpers.api.request_api",
                                 side_effect=APIError(requests.RequestException(), "TestException"))
        mock_api = api_patcher.start()

        self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args), "TestException")

        # Exception at second request
        mock_api.side_effect = side_effect

        self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args), "TestException")

        api_patcher.stop()

    def test_rtxkcd_flawedresponse(self):
        def side_effect(*args, **kwargs):
            """Emulate call and restart patcher to use default side_effect for second request."""
            api_patcher.stop()
            try:
                r = requests.get(*args, **kwargs)
            except requests.RequestException as e:
                self.skipTest(
                    "Error while emulating request in test_rtxkcd_flawedresponse: {}".format(e)
                )
            api_patcher.start()
            return r

        # 404 response after first request
        api_patcher = mock.patch("vmbot.helpers.api.request_api", side_effect=flawed_response)
        mock_api = api_patcher.start()

        self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args),
                         "Error while parsing response")

        # 404 response after second request
        mock_api.side_effect = side_effect

        self.assertRegexpMatches(self.fun.rtxkcd(self.default_mess, self.default_args),
                                 r"Failed to load xkcd #\d+ from https://xkcd\.com/\d+/")

        api_patcher.stop()

    def test_urban(self):
        self.assertRegexpMatches(self.fun.urban(self.default_mess, "API"),
                                 (r'<a href=".+">[\S ]+</a> by <em>[\S ]+</em> '
                                  r"rated (?:\+|-)\d+<br />.+"))

    def test_urban_random(self):
        self.assertRegexpMatches(self.fun.rtud(self.default_mess, self.default_args),
                                 (r'<a href=".+">[\S ]+</a> by <em>[\S ]+</em> '
                                  r"rated (?:\+|-)\d+<br />.+"))

    @mock.patch("cgi.escape", return_value="[API]")
    def test_urban_link(self, mock_cgi):
        self.assertIn('<a href="https://www.urbandictionary.com/define.php?term=API">API</a>',
                      self.fun.urban(self.default_mess, "API"))

    @mock.patch("requests.Response.json", return_value={'list': []})
    def test_urban_unknown(self, mock_json):
        self.assertEqual(self.fun.urban(self.default_mess, "API"),
                         'Failed to find any definitions for "API"')

    @mock.patch("vmbot.helpers.api.request_api",
                side_effect=APIError(requests.RequestException(), "TestException"))
    def test_urban_APIError(self, mock_api):
        self.assertRegexpMatches(self.fun.urban(self.default_mess, "API"), "TestException")

    @mock.patch("vmbot.helpers.api.request_api", side_effect=flawed_response)
    def test_urban_flawedresponse(self, mock_api):
        self.assertEqual(self.fun.urban(self.default_mess, "API"), "Error while parsing response")


if __name__ == "__main__":
    unittest.main()
