import unittest

from vmbot.helpers.format import formatTickers


class TestFormat(unittest.TestCase):
    def test_formatTickers(self):
        self.assertEqual(formatTickers("CORP", "ALLIANCE"), "[CORP] <span>&lt;ALLIANCE&gt;</span>")


if __name__ == "__main__":
    unittest.main()
