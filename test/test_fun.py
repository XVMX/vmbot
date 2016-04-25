import unittest
import mock

import os
import re

import requests
from bs4 import BeautifulSoup

from vmbot.helpers.files import EMOTES

from vmbot.fun import Fun


class TestFun(unittest.TestCase):
    defaultMess = "SenderName"
    defaultArgs = ""

    def setUp(self):
        self.fun = Fun()

    def tearDown(self):
        del self.fun

    def test_rtd(self):
        with open(EMOTES, 'r') as emotesFile:
            emotes = [emote.split()[-1] for emote in emotesFile.read().split('\n')if emote.split()]

        self.assertIn(self.fun.rtd(self.defaultMess, self.defaultArgs), emotes)

    def test_rtq(self):
        res = self.fun.rtq(self.defaultMess, self.defaultArgs)

        try:
            quoteURL = re.search("http://bash\.org/\?\d+", res).group(0)
        except AttributeError:
            self.skipTest("rtq didn't return an http://bash.org link in test_rtq")

        try:
            r = requests.get(quoteURL, timeout=5)
        except requests.exceptions.RequestException as e:
            self.skipTest("Error while connecting to http://bash.org: {} in test_rtq".format(e))
        soup = BeautifulSoup(r.text, "html.parser")

        try:
            quote = soup.find("p", class_="qt").text.encode("ascii", "replace")
        except AttributeError:
            self.skipTest("Failed to load quote from {} in test_rtq".format(quoteURL))

        self.assertEqual(res, "{}\n{}".format(quote, quoteURL))

    def test_rtq_RequestException(self):
        desc = "TestException"
        exceptionText = "Error while connecting to http://bash.org: {}".format(desc)

        # Exception at first request
        requestsPatcher = mock.patch("requests.get",
                                     side_effect=requests.exceptions.RequestException(desc))
        mockRequests = requestsPatcher.start()
        self.assertEqual(self.fun.rtq(self.defaultMess, self.defaultArgs), exceptionText)

        # Exception at second request
        def side_effect(*args, **kwargs):
            requestsPatcher.stop()
            r = requests.get(*args, **kwargs)
            mockRequests = requestsPatcher.start()
            return r

        mockRequests.side_effect = side_effect
        self.assertEqual(self.fun.rtq(self.defaultMess, self.defaultArgs), exceptionText)

        requestsPatcher.stop()

    def test_rtq_flawedResponse(self):
        def flawed_response(*args, **kwargs):
            class Object(object):
                pass

            obj = Object()
            obj.text = "This is not a valid HTML document"
            obj.status_code = 404
            return obj

        # No quotes after first request
        requestsPatcher = mock.patch("requests.get", side_effect=flawed_response)
        mockRequests = requestsPatcher.start()
        self.assertEqual(self.fun.rtq(self.defaultMess, self.defaultArgs),
                         "Failed to load any quotes from http://bash.org/?random")

        # No quote after second request
        def side_effect(*args, **kwargs):
            requestsPatcher.stop()
            r = requests.get(*args, **kwargs)
            mockRequests = requestsPatcher.start()
            return r

        mockRequests.side_effect = side_effect
        self.assertRegexpMatches(self.fun.rtq(self.defaultMess, self.defaultArgs),
                                 "Failed to load quote #\d+ from http://bash\.org/\?\d+")

        requestsPatcher.stop()

    def test_rtxkcd(self):
        res = self.fun.rtxkcd(self.defaultMess, self.defaultArgs)

        try:
            comicURL = re.search("https://xkcd\.com/\d+/", res).group(0)
        except AttributeError:
            self.skipTest("rtxkcd didn't return an https://xkcd.com link in test_rtxkcd")

        try:
            comicData = requests.get("{}info.0.json".format(comicURL), timeout=5).json()
        except requests.exceptions.RequestException as e:
            self.skipTest("Error while connecting to https://xkcd.com: {} in test_rtxkcd".format(e))
        except ValueError:
            self.skipTest("Failed to load xkcd from {} in test_rtxkcd".format(comicURL))

        self.assertEqual(res, "<b>{}</b>: {}".format(comicData['title'], comicURL))

    def test_rtxkcd_RequestException(self):
        desc = "TestException"
        exceptionText = "Error while connecting to https://xkcd.com: {}".format(desc)

        # Exception at first request
        requestsPatcher = mock.patch("requests.get",
                                     side_effect=requests.exceptions.RequestException(desc))
        mockRequests = requestsPatcher.start()
        self.assertEqual(self.fun.rtxkcd(self.defaultMess, self.defaultArgs), exceptionText)

        # Exception at second request
        def side_effect(*args, **kwargs):
            requestsPatcher.stop()
            r = requests.get(*args, **kwargs)
            mockRequests = requestsPatcher.start()
            return r

        mockRequests.side_effect = side_effect
        self.assertEqual(self.fun.rtxkcd(self.defaultMess, self.defaultArgs), exceptionText)

        requestsPatcher.stop()

    def test_rtxkcd_flawedResponse(self):
        # Exception after first JSON parsing
        requestsPatcher = mock.patch("requests.Response.json",
                                     side_effect=ValueError("No JSON object could be decoded"))
        mockRequests = requestsPatcher.start()
        self.assertEqual(self.fun.rtxkcd(self.defaultMess, self.defaultArgs),
                         "Error while parsing response from https://xkcd.com")

        # Exception after second JSON parsing
        def side_effect(*args, **kwargs):
            requestsPatcher.stop()
            try:
                res = requests.get("https://xkcd.com/info.0.json", timeout=3).json()
            except requests.exceptions.RequestException, ValueError:
                self.skipTest("Failed to pass patched JSON in test_rtxkcd_flawedResponse")
            mockRequests = requestsPatcher.start()
            return res

        mockRequests.side_effect = side_effect
        self.assertRegexpMatches(self.fun.rtxkcd(self.defaultMess, self.defaultArgs),
                                 "Failed to load xkcd #\d+ from https://xkcd\.com/\d+/")

        requestsPatcher.stop()


if __name__ == "__main__":
    unittest.main()
