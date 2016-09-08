# coding: utf-8

import unittest

from vmbot.helpers.format import format_tickers, disambiguate


class TestFormat(unittest.TestCase):
    simple_disambiguate_template = 'Other {} like "{}": {}'
    extended_disambiguate_template = simple_disambiguate_template + ", and {} others"

    def test_format_tickers(self):
        self.assertEqual(format_tickers("CORP", "ALLIANCE"), "[CORP] <span>&lt;ALLIANCE&gt;</span>")

    def test_disambiguate_simple(self):
        self.assertEqual(
            disambiguate("Default", ["Test1", "Test2"], "Cat"),
            self.simple_disambiguate_template.format("Cat", "Default", "Test1, Test2")
        )

    def test_disambiguate_extended(self):
        self.assertEqual(
            disambiguate("Default", ["Test1", "Test2", "Test3", "Test4"], "Cat"),
            self.extended_disambiguate_template.format("Cat", "Default", "Test1, Test2, Test3", 1)
        )


if __name__ == "__main__":
    unittest.main()
