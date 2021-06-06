# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from vmbot.helpers import staticdata


class TestStaticdata(unittest.TestCase):
    def test_type_name(self):
        # type_id: 34 Tritanium
        self.assertEqual(staticdata.type_name(34), "Tritanium")

    def test_type_name_invaliditem(self):
        self.assertEqual(staticdata.type_name(-1), "{Failed to load}")

    def test_region_data(self):
        # region_id: 10000002 The Forge
        self.assertDictEqual(
            staticdata.region_data(10000002),
            {'region_id': 10000002, 'region_name': "The Forge"}
        )

    def test_region_data_invalidregion(self):
        self.assertDictEqual(
            staticdata.region_data(-1),
            {'region_id': 0, 'region_name': "{Failed to load}"}
        )

    def test_system_data(self):
        # system_id: 30000142 Jita
        self.assertDictEqual(
            staticdata.system_data(30000142),
            {'system_id': 30000142, 'system_name': "Jita",
             'constellation_id': 20000020, 'constellation_name': "Kimotoro",
             'region_id': 10000002, 'region_name': "The Forge"}
        )

    def test_system_data_invalidsystem(self):
        self.assertDictEqual(
            staticdata.system_data(-1),
            {'system_id': 0, 'system_name': "{Failed to load}",
             'constellation_id': 0, 'constellation_name': "{Failed to load}",
             'region_id': 0, 'region_name': "{Failed to load}"}
        )

    def test_item_name(self):
        # item_id: 40009082 Jita IV
        self.assertEqual(staticdata.item_name(40009082), "Jita IV")

    def test_item_name_invaliditem(self):
        self.assertEqual(staticdata.item_name(-1), "{Failed to load}")

    def test_faction_name(self):
        # faction_id: 500001 Caldari State
        self.assertEqual(staticdata.faction_name(500001), "Caldari State")

    def test_faction_name_invalidfaction(self):
        self.assertEqual(staticdata.faction_name(-1), "{Failed to load}")

    def test_system_stations(self):
        # system_id: 30000001 Tanoo
        # station_ids: 60012526, 60014437
        self.assertListEqual(staticdata.system_stations(30000001), [60012526, 60014437])

    def test_system_stations_empty(self):
        # system_id: 30000004 Jark
        self.assertListEqual(staticdata.system_stations(30000004), [])

    def test_system_stations_invalidsystem(self):
        self.assertListEqual(staticdata.system_stations(-1), [])


if __name__ == "__main__":
    unittest.main()
