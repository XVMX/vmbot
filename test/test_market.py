# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import timedelta

from vmbot.models.market import MarketStructure

ESI_STRUCTURE = {
    "name": "V-3YG7 VI - The Capital",
    "owner_id": 109299958,
    "solar_system_id": 30000142,
    "type_id": 35833
}


class TestMarketStructure(unittest.TestCase):
    def test_from_esi_result(self):
        s = MarketStructure.from_esi_result(12345, ESI_STRUCTURE)
        self.assertEqual(s.structure_id, 12345)
        self.assertEqual(s.system_id, ESI_STRUCTURE["solar_system_id"])
        self.assertEqual(s.type_id, ESI_STRUCTURE["type_id"])
        self.assertTrue(s.has_market)
        self.assertIsInstance(s.update_age, timedelta)

    def test_from_esi_denied(self):
        s = MarketStructure.from_esi_denied(12345)
        self.assertEqual(s.structure_id, 12345)
        self.assertIsNone(s.system_id)
        self.assertIsNone(s.type_id)
        self.assertFalse(s.has_market)
        self.assertIsInstance(s.update_age, timedelta)


if __name__ == "__main__":
    unittest.main()
