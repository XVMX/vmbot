# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime

from vmbot.helpers.format import (format_ref_type, format_affil, format_tickers,
                                  format_jid_nick, disambiguate)


class TestFormat(unittest.TestCase):
    _base_affil_template = (" <strong>{} [{}]</strong> in <strong>{} "
                            "&lt;{}&gt;</strong>, which belongs to the <strong>{}</strong>")
    char_affil_template = ("<strong>{}</strong> ({:+.2f}, born {:%m/%Y}) is part of"
                           + _base_affil_template)
    structure_affil_template = "The structure is owned by" + _base_affil_template

    simple_disambiguate_template = 'Other {} like "{}": {}'
    extended_disambiguate_template = simple_disambiguate_template + ", and {:,} others"

    def test_format_ref_type(self):
        self.assertEqual(format_ref_type("abc_def"), "Abc Def")

    def test_format_character(self):
        birthday = datetime(year=2020, month=07, day=5, hour=16, minute=39, second=0)
        self.assertEqual(
            format_affil("A", 2.3, birthday, "B", "C", "D", "E", "F"),
            self.char_affil_template.format("A", 2.3, birthday, "B", "E", "C", "F", "D")
        )

    def test_format_structure(self):
        self.assertEqual(
            format_affil(None, None, None, "B", "C", "D", "E", "F"),
            self.structure_affil_template.format("B", "E", "C", "F", "D")
        )

    def test_format_tickers(self):
        self.assertEqual(format_tickers("CORP", "ALLIANCE"), "[CORP] <ALLIANCE>")

    def test_format_tickers_html(self):
        self.assertEqual(format_tickers("CORP", "ALLIANCE", html=True), "[CORP] &lt;ALLIANCE&gt;")

    def test_format_jid_nick(self):
        self.assertEqual(format_jid_nick("user@domain.tld", "nick"), "nick (user)")

    def test_format_jid_nick_nonick(self):
        self.assertEqual(format_jid_nick("user@domain.tld", None), "user")

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
