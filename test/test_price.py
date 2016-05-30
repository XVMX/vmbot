import unittest
import mock

import os

from vmbot.helpers.files import CACHE_DB
from vmbot.helpers.exceptions import APIError

from vmbot.utils import Price


class TestPrice(unittest.TestCase):
    defaultMess = "SenderName"
    defaultArgs = ""

    priceTemplate = ("<b>{}</b> in <b>{}</b>:<br />"
                     "Sells: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                     "Buys: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                     "Spread: {:,.2%}")
    noSpreadTemplate = ("<b>{}</b> in <b>{}</b>:<br />"
                        "Sells: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                        "Buys: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                        "Spread: NaNNaNNaNNaNNaNBatman!")

    simpleDisambiguateTemplate = "<br />Other {} like \"{}\": {}"
    extendedDisambiguateTemplate = simpleDisambiguateTemplate + ", and {} others"

    def setUp(self):
        self.price = Price()

    def tearDown(self):
        del self.price

    @classmethod
    def setUpClass(cls):
        # Delete cache.db before testing
        try:
            os.remove(CACHE_DB)
        except:
            pass

    def test_price_noargs(self):
        self.assertEqual(
            self.price.price(self.defaultMess, self.defaultArgs),
            "Please provide an item name and optionally a system name: <item>@[system]"
        )

    def test_price_excessargs(self):
        self.assertEqual(
            self.price.price(self.defaultMess, "item@system@excess"),
            "Please provide an item name and optionally a system name: <item>@[system]"
        )

    @mock.patch("vmbot.utils.Price._getMarketOrders", return_value=[(1000, 45.99), (1000, 45.99)])
    def test_price_nosystem(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite"),
            self.priceTemplate.format("Pyerite", "Jita", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._getMarketOrders", return_value=[(1000, 45.99), (1000, 45.99)])
    def test_price_plex_nosystem(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Plex"),
            self.priceTemplate.format("30 Day Pilot's License Extension (PLEX)",
                                      "Jita", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._getMarketOrders", return_value=[(1000, 45.99), (1000, 45.99)])
    def test_price_system(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite@Amarr"),
            self.priceTemplate.format("Pyerite", "Amarr", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._getMarketOrders", return_value=[(1000, 45.99), (1000, 45.99)])
    def test_price_disambiguate(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Tritanium@Hek"),
            (self.priceTemplate.format("Tritanium", "Hek", 45.99, 1000, 45.99, 1000, 0) +
             self.simpleDisambiguateTemplate.format("items", "Tritanium", "Alloyed Tritanium Bar") +
             self.simpleDisambiguateTemplate.format("systems", "Hek", "Ghekon"))
        )

    def test_price_invaliditem(self):
        self.assertEqual(
            self.price.price(self.defaultMess, "InvalidItem"),
            "Can't find a matching item"
        )

    def test_price_invalidsystem(self):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite@InvalidSystem"),
            "Can't find a matching system"
        )

    @mock.patch("vmbot.utils.Price._getMarketOrders", side_effect=APIError("TestException"))
    def test_price_APIError(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite"),
            "TestException"
        )

    @mock.patch("vmbot.utils.Price._getMarketOrders", return_value=[(0, 0), (0, 0)])
    def test_price_noorders(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite"),
            self.noSpreadTemplate.format("Pyerite", "Jita", 0, 0, 0, 0)
        )

    def test_disambiguate_simple(self):
        self.assertEqual(
            self.price._disambiguate("Default", ["Test1", "Test2"], "Cat"),
            self.simpleDisambiguateTemplate.format("Cat", "Default", "Test1, Test2")
        )

    def test_disambiguate_extended(self):
        self.assertEqual(
            self.price._disambiguate("Default", ["Test1", "Test2", "Test3", "Test4"], "Cat"),
            self.extendedDisambiguateTemplate.format("Cat", "Default", "Test1, Test2, Test3", 1)
        )

    def test_getMarketOrders(self):
        # The Forge
        regionID = 10000002
        # Tritanium
        itemTypeID = 34

        res = self.price._getMarketOrders(regionID, "Jita", itemTypeID)
        self.assertIsInstance(res[0][0], (int, long))
        self.assertIsInstance(res[0][1], float)
        self.assertIsInstance(res[1][0], (int, long))
        self.assertIsInstance(res[1][1], float)

    @mock.patch("vmbot.helpers.api.getCRESTEndpoint", return_value={'items': []})
    def test_getPriceVolume_noorders(self, mockCRESTEndpoint):
        # The Forge
        regionID = 10000002
        # Pyerite
        itemTypeID = 35

        res = self.price._getMarketOrders(regionID, "Jita", itemTypeID)
        self.assertEqual(res[0][0], 0)
        self.assertEqual(res[0][1], 0)
        self.assertEqual(res[1][0], 0)
        self.assertEqual(res[1][1], 0)


if __name__ == "__main__":
    unittest.main()
