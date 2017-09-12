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

    def test_solarSystemData(self):
        # solarSystemID: 30000142 Jita
        self.assertDictEqual(
            staticdata.solarSystemData(30000142),
            {'solarSystemID': 30000142, 'solarSystemName': "Jita",
             'constellationID': 20000020, 'constellationName': "Kimotoro",
             'regionID': 10000002, 'regionName': "The Forge"}
        )

    def test_solarSystemData_invalidsystem(self):
        self.assertDictEqual(
            staticdata.solarSystemData(-1),
            {'solarSystemID': 0, 'solarSystemName': "{Failed to load}",
             'constellationID': 0, 'constellationName': "{Failed to load}",
             'regionID': 0, 'regionName': "{Failed to load}"}
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
