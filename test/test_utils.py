import unittest
import mock

import os

import requests

from vmbot.utils import EveUtils, APIError


class TestUtils(unittest.TestCase):
    defaultMess = "SenderName"
    defaultArgs = ""

    def setUp(self):
        self.utils = EveUtils()

    def tearDown(self):
        del self.utils

    def test_getTypeName(self):
        self.assertEqual(self.utils.getTypeName(34), "Tritanium")

    def test_getTypeName_invaliditem(self):
        self.assertEqual(self.utils.getTypeName(-1), "{Failed to load}")

    def test_getSolarSystemData(self):
        self.assertDictEqual(
            self.utils.getSolarSystemData(30000142),
            {'solarSystemID': 30000142, 'solarSystemName': "Jita",
             'constellationID': 20000020, 'constellationName': "Kimotoro",
             'regionID': 10000002, 'regionName': "The Forge"}
        )

    def test_getSolarSystemData_invalidsystem(self):
        self.assertDictEqual(
            self.utils.getSolarSystemData(-1),
            {'solarSystemID': 0, 'solarSystemName': "{Failed to load}",
             'constellationID': 0, 'constellationName': "{Failed to load}",
             'regionID': 0, 'regionName': "{Failed to load}"}
        )

    def test_formatTickers(self):
        self.assertEqual(self.utils.formatTickers("CORP", "ALLIANCE"),
                         "[CORP] <span>&lt;ALLIANCE&gt;</span>")


if __name__ == "__main__":
    unittest.main()
