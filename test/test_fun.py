# coding: utf-8

import unittest
import mock

import re

import requests
from bs4 import BeautifulSoup

from vmbot.helpers.files import EMOTES

from vmbot.fun import Fun


def flawed_response(*args, **kwargs):
    """Return a requests.Response with 404 status code."""
    res = requests.Response()
    res.status_code = 404
    res._content = b"ASCII text"
    res.encoding = "ascii"
    return res


class TestFun(unittest.TestCase):
    default_mess = ""
    default_args = ""

    def setUp(self):
        self.fun = Fun()

    def tearDown(self):
        del self.fun

    def test_rtd(self):
        with open(EMOTES, 'r') as emotes_file:
            emotes = emotes_file.read()

        self.assertIn(self.fun.rtd(self.default_mess, self.default_args), emotes)

    def test_rtq(self):
        res = self.fun.rtq(self.default_mess, self.default_args)

        try:
            quote_url = re.search("http://bash\.org/\?\d+", res).group(0)
        except AttributeError:
            self.fail("rtq didn't return an http://bash.org link in test_rtq")

        try:
            r = requests.get(quote_url, timeout=5)
        except requests.exceptions.RequestException as e:
            self.skipTest("Error while connecting to http://bash.org in test_rtq: {}".format(e))
        soup = BeautifulSoup(r.text, "html.parser")

        try:
            quote = soup.find("p", class_="qt").text.encode("ascii", "replace")
        except AttributeError:
            self.skipTest("Failed to load quote from {} in test_rtq".format(quote_url))

        self.assertEqual(res, "{}\n{}".format(quote_url, quote))

    def test_rtq_RequestException(self):
        desc = "TestException"
        exception_text = "Error while connecting to http://bash.org: {}".format(desc)

        def side_effect(*args, **kwargs):
            """Emulate call and restart patcher to use default side_effect for second request."""
            requests_patcher.stop()
            try:
                r = requests.get(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                self.skipTest(
                    "Error while emulating request in test_rtq_RequestException: {}".format(e)
                )
            mock_requests = requests_patcher.start()
            return r

        # Exception at first request
        requests_patcher = mock.patch("requests.get",
                                      side_effect=requests.exceptions.RequestException(desc))
        mock_requests = requests_patcher.start()

        self.assertEqual(self.fun.rtq(self.default_mess, self.default_args), exception_text)

        # Exception at second request
        mock_requests.side_effect = side_effect

        self.assertEqual(self.fun.rtq(self.default_mess, self.default_args), exception_text)

        requests_patcher.stop()

    def test_rtq_flawedresponse(self):
        def side_effect(*args, **kwargs):
            """Emulate call and restart patcher to use default side_effect for second request."""
            requests_patcher.stop()
            try:
                r = requests.get(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                self.skipTest(
                    "Error while emulating request in test_rtq_flawedresponse: {}".format(e)
                )
            mock_requests = requests_patcher.start()
            return r

        # 404 response after first request
        requests_patcher = mock.patch("requests.get", side_effect=flawed_response)
        mock_requests = requests_patcher.start()

        self.assertEqual(self.fun.rtq(self.default_mess, self.default_args),
                         "Failed to load any quotes from http://bash.org/?random")

        # 404 response after second request
        mock_requests.side_effect = side_effect

        self.assertRegexpMatches(self.fun.rtq(self.default_mess, self.default_args),
                                 "Failed to load quote #\d+ from http://bash\.org/\?\d+")

        requests_patcher.stop()

    def test_rtxkcd(self):
        res = self.fun.rtxkcd(self.default_mess, self.default_args)

        try:
            comic_url = re.search("https://xkcd\.com/\d+/", res).group(0)
        except AttributeError:
            self.fail("rtxkcd didn't return an https://xkcd.com link in test_rtxkcd")

        try:
            comic_data = requests.get("{}info.0.json".format(comic_url), timeout=5).json()
        except requests.exceptions.RequestException as e:
            self.skipTest("Error while connecting to https://xkcd.com in test_rtxkcd: {}".format(e))
        except ValueError:
            self.skipTest("Failed to load xkcd from {} in test_rtxkcd".format(comic_url))

        self.assertEqual(res, "<b>{}</b>: {}".format(comic_data['title'], comic_url))

    def test_rtxkcd_RequestException(self):
        desc = "TestException"
        exception_text = "Error while connecting to https://xkcd.com: {}".format(desc)

        def side_effect(*args, **kwargs):
            """Emulate call and restart patcher to use default side_effect for second request."""
            requests_patcher.stop()
            try:
                r = requests.get(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                self.skipTest(
                    "Error while emulating request in test_rtxkcd_RequestException: {}".format(e)
                )
            mock_requests = requests_patcher.start()
            return r

        # Exception at first request
        requests_patcher = mock.patch("requests.get",
                                      side_effect=requests.exceptions.RequestException(desc))
        mock_requests = requests_patcher.start()

        self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args), exception_text)

        # Exception at second request
        mock_requests.side_effect = side_effect

        self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args), exception_text)

        requests_patcher.stop()

    def test_rtxkcd_flawedresponse(self):
        def side_effect(*args, **kwargs):
            """Emulate call and restart patcher to use default side_effect for second request."""
            requests_patcher.stop()
            try:
                r = requests.get(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                self.skipTest(
                    "Error while emulating request in test_rtxkcd_flawedresponse: {}".format(e)
                )
            mock_requests = requests_patcher.start()
            return r

        # 404 response after first request
        requests_patcher = mock.patch("requests.get", side_effect=flawed_response)
        mock_requests = requests_patcher.start()

        self.assertEqual(self.fun.rtxkcd(self.default_mess, self.default_args),
                         "Error while parsing response from https://xkcd.com")

        # 404 response after second request
        mock_requests.side_effect = side_effect

        self.assertRegexpMatches(self.fun.rtxkcd(self.default_mess, self.default_args),
                                 "Failed to load xkcd #\d+ from https://xkcd\.com/\d+/")

        requests_patcher.stop()

    def test_urban(self):
        self.assertRegexpMatches(self.fun.urban(self.default_mess, "API"),
                                 "<b>[\w\d ]+</b> by <i>[\w\d ]+</i> rated (?:\+|-)\d+: .+<br />.+")

    def test_urban_random(self):
        self.assertRegexpMatches(self.fun.rtud(self.default_mess, self.default_args),
                                 "<b>[\w\d ]+</b> by <i>[\w\d ]+</i> rated (?:\+|-)\d+: .+<br />.+")

    @mock.patch("cgi.escape", return_value="[API]")
    def test_urban_link(self, mock_cgi):
        self.assertIn('<a href="https://www.urbandictionary.com/define.php?term=API">API</a>',
                      self.fun.urban(self.default_mess, "API"))

    @mock.patch("requests.Response.json", return_value={'list': []})
    def test_urban_unknown(self, mock_requests):
        self.assertEqual(self.fun.urban(self.default_mess, "API"),
                         'Failed to find any definitions for "API"')

    @mock.patch("requests.get", side_effect=requests.exceptions.RequestException)
    def test_urban_RequestException(self, mock_requests):
        self.assertRegexpMatches(self.fun.urban(self.default_mess, "API"),
                                 "Error while connecting to https://www.urbandictionary.com: .*")

    @mock.patch("requests.get", side_effect=flawed_response)
    def test_urban_flawedresponse(self, mock_requests):
        self.assertEqual(self.fun.urban(self.default_mess, "API"),
                         "Error while parsing response from https://www.urbandictionary.com")


if __name__ == "__main__":
    unittest.main()
