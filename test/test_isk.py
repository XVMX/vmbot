import unittest

from vmbot.utils import ISK


class TestConfig(unittest.TestCase):
    largeIskValue = float(1234567890000)
    smallIskValue = float(123456.78)

    def setUp(self):
        self.largeIsk = ISK(self.largeIskValue)
        self.smallIsk = ISK(self.smallIskValue)

    def tearDown(self):
        del self.largeIsk
        del self.smallIsk

    def test_empty_constructor(self):
        self.assertEqual(ISK(), float())

    def test_value(self):
        self.assertEqual(self.largeIsk, self.largeIskValue)
        self.assertEqual(self.smallIsk, self.smallIskValue)

    def test_format_nospec(self):
        self.assertEqual("{}".format(self.largeIsk), "1.23456789t")
        self.assertEqual("{}".format(self.smallIsk), "123.45678k")

    def test_format_spec(self):
        self.assertEqual("{:.2f}".format(self.largeIsk), "1.23t")
        self.assertEqual("{:.2f}".format(self.smallIsk), "123.46k")


if __name__ == "__main__":
    unittest.main()
