# coding: utf-8

import unittest

from vmbot.models.isk import ISK


class TestISK(unittest.TestCase):
    large_isk_value = float(1234567890000)
    small_isk_value = float(123456.78)

    def setUp(self):
        self.large_isk = ISK(self.large_isk_value)
        self.small_isk = ISK(self.small_isk_value)

    def tearDown(self):
        del self.large_isk
        del self.small_isk

    def test_empty_constructor(self):
        self.assertEqual(ISK(), float())

    def test_value(self):
        self.assertEqual(self.large_isk, self.large_isk_value)
        self.assertEqual(self.small_isk, self.small_isk_value)

    def test_format_nospec(self):
        self.assertEqual("{}".format(self.large_isk), "1.23456789t")
        self.assertEqual("{}".format(self.small_isk), "123.45678k")

    def test_format_spec(self):
        self.assertEqual("{:.2f}".format(self.large_isk), "1.23t")
        self.assertEqual("{:.2f}".format(self.small_isk), "123.46k")


if __name__ == "__main__":
    unittest.main()
