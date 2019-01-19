# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime, timedelta

from vmbot.helpers import time


class TestTime(unittest.TestCase):
    def test_rfc822_fmt(self):
        self.assertEqual(
            datetime.strptime("Fri, 20 Apr 2018 14:00:00 GMT", time.RFC822_DATETIME_FMT),
            datetime(year=2018, month=4, day=20, hour=14, minute=0, second=0)
        )

        self.assertRaises(ValueError, datetime.strptime,
                          "2018-07-09T14:43:21Z", time.RFC822_DATETIME_FMT)

    def test_iso8601_fmt(self):
        self.assertEqual(datetime.strptime("2018-07-09T14:43:21Z", time.ISO8601_DATETIME_FMT),
                         datetime(year=2018, month=7, day=9, hour=14, minute=43, second=21))

        self.assertRaises(ValueError, datetime.strptime,
                          "Fri, 20 Apr 2018 14:00:00 GMT", time.ISO8601_DATETIME_FMT)

    def test_iso8601_micro_fmt(self):
        self.assertEqual(
            datetime.strptime("2018-07-09T14:43:21.602741Z", time.ISO8601_DATETIME_MICRO_FMT),
            datetime(year=2018, month=7, day=9, hour=14, minute=43, second=21, microsecond=602741)
        )

        self.assertRaises(ValueError, datetime.strptime,
                          "2018-07-09T14:43:21Z", time.ISO8601_DATETIME_MICRO_FMT)
        self.assertRaises(ValueError, datetime.strptime,
                          "Fri, 20 Apr 2018 14:00:00 GMT", time.ISO8601_DATETIME_MICRO_FMT)

    def test_parse_iso8601_duration(self):
        self.assertEqual(time.parse_iso8601_duration("5 days"), None)

        self.assertEqual(time.parse_iso8601_duration("P5DT3H15M22,632S"),
                         timedelta(days=5, hours=3, minutes=15, seconds=22.632))
        self.assertEqual(
            time.parse_iso8601_duration("P3Y4M7W1DT5H53M36.7939S"),
            timedelta(weeks=7, days=3 * 365 + 4 * 30 + 1, hours=5, minutes=53, seconds=36.7939)
        )

    def test_parse_iso8601_duration_empty(self):
        self.assertEqual(time.parse_iso8601_duration("P"), timedelta(seconds=0))
        self.assertEqual(time.parse_iso8601_duration("PT"), timedelta(seconds=0))

    def test_parse_iso8601_duration_decerror(self):
        self.assertEqual(time.parse_iso8601_duration("PT5.312,642S"), None)
        self.assertEqual(time.parse_iso8601_duration("P6.643DT22,53M"), None)


if __name__ == "__main__":
    unittest.main()
