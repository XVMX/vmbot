# coding: utf-8

import unittest

from vmbot.helpers.format import format_tickers


class TestFormat(unittest.TestCase):
    def test_format_tickers(self):
        self.assertEqual(format_tickers("CORP", "ALLIANCE"), "[CORP] <span>&lt;ALLIANCE&gt;</span>")


if __name__ == "__main__":
    unittest.main()
