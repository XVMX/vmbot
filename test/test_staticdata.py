# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from vmbot.helpers import staticdata


class TestStaticdata(unittest.TestCase):
    def test_get_sde_conn(self):
        with staticdata._get_sde_conn() as c:
            conn = c
        with staticdata._get_sde_conn() as c:
            self.assertIs(c, conn)

    def test_type_name(self):
        # type_id: 34 Tritanium
        self.assertEqual(staticdata.type_name.__wrapped__(34), "Tritanium")

    def test_type_name_invaliditem(self):
        self.assertEqual(staticdata.type_name.__wrapped__(-1), "{Failed to load}")

    def test_search_market_types(self):
        # types: 34 Tritanium, 25595 Alloyed Tritanium Bar
        self.assertListEqual(staticdata.search_market_types("trit"),
                             [(34, "Tritanium"), (25595, "Alloyed Tritanium Bar")])

    def test_search_market_types_empty(self):
        self.assertListEqual(staticdata.search_market_types("InvalidItem"), [])

    def test_region_data(self):
        # region_id: 10000002 The Forge
        self.assertDictEqual(
            staticdata.region_data.__wrapped__(10000002),
            {'region_id': 10000002, 'region_name': "The Forge"}
        )

    def test_region_data_invalidregion(self):
        self.assertDictEqual(
            staticdata.region_data.__wrapped__(-1),
            {'region_id': 0, 'region_name': "{Failed to load}"}
        )

    def test_system_data(self):
        # system_id: 30000142 Jita
        self.assertDictEqual(
            staticdata.system_data.__wrapped__(30000142),
            {'system_id': 30000142, 'system_name': "Jita",
             'constellation_id': 20000020, 'constellation_name': "Kimotoro",
             'region_id': 10000002, 'region_name': "The Forge"}
        )

    def test_system_data_invalidsystem(self):
        self.assertDictEqual(
            staticdata.system_data.__wrapped__(-1),
            {'system_id': 0, 'system_name': "{Failed to load}",
             'constellation_id': 0, 'constellation_name': "{Failed to load}",
             'region_id': 0, 'region_name': "{Failed to load}"}
        )

    def test_item_name(self):
        # item_id: 40009082 Jita IV
        self.assertEqual(staticdata.item_name.__wrapped__(40009082), "Jita IV")

    def test_item_name_invaliditem(self):
        self.assertEqual(staticdata.item_name.__wrapped__(-1), "{Failed to load}")

    def test_faction_name(self):
        # faction_id: 500001 Caldari State
        self.assertEqual(staticdata.faction_name.__wrapped__(500001), "Caldari State")

    def test_faction_name_invalidfaction(self):
        self.assertEqual(staticdata.faction_name.__wrapped__(-1), "{Failed to load}")

    def test_system_stations(self):
        # system_id: 30000001 Tanoo
        # station_ids: 60012526, 60014437
        self.assertSetEqual(staticdata.system_stations(30000001), {60012526, 60014437})

    def test_system_stations_empty(self):
        # system_id: 30000004 Jark
        self.assertSetEqual(staticdata.system_stations(30000004), set())

    def test_system_stations_invalidsystem(self):
        self.assertSetEqual(staticdata.system_stations(-1), set())

    def test_market_structure_types(self):
        # types: 35834 Keepstar, 35826 Azbel, 35836 Tatara
        market_structures = staticdata.market_structure_types.__wrapped__()
        self.assertIn(35834, market_structures)
        self.assertIn(35826, market_structures)
        self.assertIn(35836, market_structures)


if __name__ == "__main__":
    unittest.main()
