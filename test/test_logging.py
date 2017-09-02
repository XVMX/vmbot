# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import logging

import requests

from vmbot.helpers.logging import GitHubIssueHandler


class TestGitHubIssueHandler(unittest.TestCase):
    def setUp(self):
        GitHubIssueHandler.known_issues.clear()
        self.handler = GitHubIssueHandler("owner", "repo", "user", "token")

    def tearDown(self):
        del self.handler

    def test_detect_duplicate(self):
        next_res = requests.Response()
        res = requests.Response()

        next_res.status_code = res.status_code = 200
        next_res.headers['Link'] = '<TestURL>; rel="next"'
        next_res._content = b'[{"title": "TestTitle1"}]'
        res._content = b'[{"title": "TestTitle2"}]'
        next_res.encoding = res.encoding = "ascii"

        with mock.patch("requests.get", side_effect=[next_res, res]):
            self.assertTrue(self.handler._detect_duplicate("TestTitle1", ["TestLabel"]))

    def test_detect_duplicate_cached(self):
        self.handler.known_issues.add("TestTitle")
        self.assertTrue(self.handler._detect_duplicate("TestTitle"))

    @mock.patch("requests.get", side_effect=requests.exceptions.RequestException("TestException"))
    def test_detect_duplicate_RequestException(self, mock_requests):
        self.assertFalse(self.handler._detect_duplicate("TestTitle"))

    @mock.patch("vmbot.helpers.logging.GitHubIssueHandler._detect_duplicate", return_value=False)
    @mock.patch("requests.post", return_value=requests.Response())
    def test_emit(self, mock_requests, mock_handler):
        mock_requests.return_value.status_code = 201

        rec = logging.makeLogRecord({'msg': "TestTitle1\nTestBody", 'gh_labels': ["TestLabel"]})
        self.handler.emit(rec)
        self.assertIn("TestTitle1", self.handler.known_issues)

        rec = logging.makeLogRecord({'msg': "TestTitle2"})
        self.handler.emit(rec)
        self.assertIn("TestTitle2", self.handler.known_issues)

    @mock.patch("vmbot.helpers.logging.GitHubIssueHandler._detect_duplicate", return_value=True)
    def test_emit_duplicate(self, mock_handler):
        rec = logging.makeLogRecord({'msg': "TestTitle"})
        self.handler.emit(rec)
        mock_handler.assert_called()

    @mock.patch("requests.post", side_effect=requests.exceptions.RequestException("TestException"))
    @mock.patch("logging.Handler.handleError")
    def test_emit_RequestException(self, mock_handler, mock_requests):
        rec = logging.makeLogRecord({'msg': "TestTitle"})
        self.handler.emit(rec)
        mock_handler.assert_called()


if __name__ == "__main__":
    unittest.main()
