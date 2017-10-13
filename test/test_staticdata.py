# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from vmbot.helpers import staticdata


class TestStaticdata(unittest.TestCase):
    def test_typeName(self):
        # typeID: 34 Tritanium
        self.assertEqual(staticdata.typeName(34), "Tritanium")

    def test_typeName_invaliditem(self):
        self.assertEqual(staticdata.typeName(-1), "{Failed to load}")

    def test_solar_system_data(self):
        # system_id: 30000142 Jita
        self.assertDictEqual(
            staticdata.solar_system_data(30000142),
            {'system_id': 30000142, 'system_name': "Jita",
             'constellation_id': 20000020, 'constellation_name': "Kimotoro",
             'region_id': 10000002, 'region_name': "The Forge"}
        )

    def test_solar_system_data_invalidsystem(self):
        self.assertDictEqual(
            staticdata.solar_system_data(-1),
            {'system_id': 0, 'system_name': "{Failed to load}",
             'constellation_id': 0, 'constellation_name': "{Failed to load}",
             'region_id': 0, 'region_name': "{Failed to load}"}
        )

    def test_itemName(self):
        # itemID: 40009082 Jita IV
        self.assertEqual(staticdata.itemName(40009082), "Jita IV")

    def test_itemName_invaliditem(self):
        self.assertEqual(staticdata.itemName(-1), "{Failed to load}")

    def test_faction_name(self):
        # faction_id: 500001 Caldari State
        self.assertEqual(staticdata.faction_name(500001), "Caldari State")

    def test_faction_name_invalidfaction(self):
        self.assertEqual(staticdata.faction_name(-1), "{Failed to load}")


if __name__ == "__main__":
    unittest.main()
