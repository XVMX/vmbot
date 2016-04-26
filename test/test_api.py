import unittest

from vmbot.helpers import api


class TestAPI(unittest.TestCase):
    def test_getTypeName(self):
        self.assertEqual(api.getTypeName(34), "Tritanium")

    def test_getTypeName_invaliditem(self):
        self.assertEqual(api.getTypeName(-1), "{Failed to load}")

    def test_getSolarSystemData(self):
        self.assertDictEqual(
            api.getSolarSystemData(30000142),
            {'solarSystemID': 30000142, 'solarSystemName': "Jita",
             'constellationID': 20000020, 'constellationName': "Kimotoro",
             'regionID': 10000002, 'regionName': "The Forge"}
        )

    def test_getSolarSystemData_invalidsystem(self):
        self.assertDictEqual(
            api.getSolarSystemData(-1),
            {'solarSystemID': 0, 'solarSystemName': "{Failed to load}",
             'constellationID': 0, 'constellationName': "{Failed to load}",
             'regionID': 0, 'regionName': "{Failed to load}"}
        )

    def test_getTickers(self):
        # corporationID: 2052404106 [XVMX]
        # allianceID: 1354830081 <CONDI>
        self.assertTupleEqual(api.getTickers(2052404106, 1354830081), ("XVMX", "CONDI"))

    def test_getTickers_corponly(self):
        # corporationID: 2052404106 [XVMX] (member of <CONDI>)
        self.assertTupleEqual(api.getTickers(2052404106, None), ("XVMX", "CONDI"))

    def test_getTickers_allianceonly(self):
        # allianceID: 1354830081 <CONDI>
        self.assertTupleEqual(api.getTickers(None, 1354830081), (None, "CONDI"))

    def test_getTickers_invalidid(self):
        self.assertTupleEqual(api.getTickers(-1, -1), ("{Failed to load}", "{Failed to load}"))


if __name__ == "__main__":
    unittest.main()
