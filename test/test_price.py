import unittest
import mock

import os

import requests

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

    @mock.patch("vmbot.utils.Price._getPriceVolume", return_value=(1000, 45.99))
    def test_price_nosystem(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite"),
            self.priceTemplate.format("Pyerite", "Jita", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._getPriceVolume", return_value=(1000, 45.99))
    def test_price_plex_nosystem(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Plex"),
            self.priceTemplate.format("30 Day Pilot's License Extension (PLEX)",
                                      "Jita", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._getPriceVolume", return_value=(1000, 45.99))
    def test_price_system(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite@Amarr"),
            self.priceTemplate.format("Pyerite", "Amarr", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._getPriceVolume", return_value=(1000, 45.99))
    def test_price_disambiguate(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Tritanium@Hek"),
            (self.priceTemplate.format("Tritanium", "Hek", 45.99, 1000, 45.99, 1000, 0) +
             self.simpleDisambiguateTemplate.format("items", "Tritanium", "Alloyed Tritanium Bar") +
             self.simpleDisambiguateTemplate.format("systems", "Hek", "Ghekon"))
        )

    @mock.patch("vmbot.utils.Price._getPriceVolume", return_value=(1000, 45.99))
    def test_price_invaliditem(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "InvalidItem"),
            "Can't find a matching item"
        )

    @mock.patch("vmbot.utils.Price._getPriceVolume", return_value=(1000, 45.99))
    def test_price_invalidsystem(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite@InvalidSystem"),
            "Can't find a matching system"
        )

    @mock.patch("vmbot.utils.Price._getPriceVolume", side_effect=APIError("TestException"))
    def test_price_APIError(self, mockPriceVolume):
        self.assertEqual(
            self.price.price(self.defaultMess, "Pyerite"),
            "TestException"
        )

    @mock.patch("vmbot.utils.Price._getPriceVolume", return_value=(0, 0))
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

    def test_getPriceVolume_sell(self):
        # The Forge
        regionID = 10000002
        # Tritanium
        itemTypeID = 34

        res = self.price._getPriceVolume("sell", regionID, "Jita", itemTypeID)
        self.assertIsInstance(res[0], int)
        self.assertIsInstance(res[1], float)

    def test_getPriceVolume_buy(self):
        # The Forge
        regionID = 10000002
        # Tritanium
        itemTypeID = 34

        res = self.price._getPriceVolume("buy", regionID, "Jita", itemTypeID)
        self.assertIsInstance(res[0], int)
        self.assertIsInstance(res[1], float)

    @mock.patch("requests.Response.json", return_value={'items': []})
    def test_getPriceVolume_noorders(self, mockResponseJson):
        # The Forge
        regionID = 10000002
        # Tritanium
        itemTypeID = 34

        res = self.price._getPriceVolume("buy", regionID, "Jita", itemTypeID)
        self.assertEqual(res[0], 0)
        self.assertEqual(res[1], 0)

    @mock.patch("requests.get", side_effect=requests.exceptions.RequestException("TestException"))
    def test_getPriceVolume_RequestException(self, mockGet):
        # The Forge
        regionID = 10000002
        # Tritanium
        itemTypeID = 34

        self.assertRaisesRegexp(APIError, "Error while connecting to CREST: TestException",
                                self.price._getPriceVolume, "sell", regionID, "Jita", itemTypeID)

    def test_getPriceVolume_flawedResponse(self):
        # The Forge
        regionID = 10000002
        # Tritanium
        itemTypeID = 34

        def flawed_response(*args, **kwargs):
            class Object(object):
                pass

            obj = Object()
            obj.text = "This is not a valid HTML document"
            obj.status_code = 404
            return obj

        # Non-200 status
        requestsPatcher = mock.patch("requests.get", side_effect=flawed_response)
        mockRequests = requestsPatcher.start()

        self.assertRaisesRegexp(APIError, "CREST returned error code 404",
                                self.price._getPriceVolume, "sell", regionID, "Jita", itemTypeID)

        requestsPatcher.stop()


if __name__ == "__main__":
    unittest.main()
