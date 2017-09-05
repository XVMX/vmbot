# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from vmbot.helpers.format import format_affil, format_tickers, disambiguate


class TestFormat(unittest.TestCase):
    _base_affil_template = (" corporation <strong>{} [{}]</strong> in <strong>{} "
                            "&lt;{}&gt;</strong> which is part of the <strong>{}</strong>")
    char_affil_template = "<strong>{} ({:+.2f})</strong> is part of" + _base_affil_template
    structure_affil_template = "The structure is owned by" + _base_affil_template

    simple_disambiguate_template = 'Other {} like "{}": {}'
    extended_disambiguate_template = simple_disambiguate_template + ", and {} others"

    def test_format_character(self):
        self.assertEqual(
            format_affil("A", 2.3, "B", "C", "D", "E", "F"),
            self.char_affil_template.format("A", 2.3, "B", "E", "C", "F", "D")
        )

    def test_format_structure(self):
        self.assertEqual(
            format_affil("", None, "B", "C", "D", "E", "F"),
            self.structure_affil_template.format("B", "E", "C", "F", "D")
        )

    def test_format_tickers(self):
        self.assertEqual(format_tickers("CORP", "ALLIANCE"), "[CORP] <ALLIANCE>")

    def test_format_tickers_html(self):
        self.assertEqual(format_tickers("CORP", "ALLIANCE", html=True), "[CORP] &lt;ALLIANCE&gt;")

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
