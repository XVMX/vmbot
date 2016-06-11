# coding: utf-8

import unittest
import mock

import os

from vmbot.helpers.files import CACHE_DB
from vmbot.helpers.exceptions import APIError

from vmbot.utils import Price


class TestPrice(unittest.TestCase):
    default_mess = ""
    default_args = ""

    price_template = ("<b>{}</b> in <b>{}</b>:<br />"
                      "Sells: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                      "Buys: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                      "Spread: {:,.2%}")
    no_spread_template = ("<b>{}</b> in <b>{}</b>:<br />"
                          "Sells: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                          "Buys: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                          "Spread: NaNNaNNaNNaNNaNBatman!")

    simple_disambiguate_template = "<br />Other {} like \"{}\": {}"
    extended_disambiguate_template = simple_disambiguate_template + ", and {} others"

    def setUp(self):
        self.price = Price()

    def tearDown(self):
        del self.price

    @classmethod
    def setUpClass(cls):
        try:
            os.remove(CACHE_DB)
        except OSError:
            pass

    @classmethod
    def tearDownClass(cls):
        return cls.setUpClass()

    def test_price_noargs(self):
        self.assertEqual(
            self.price.price(self.default_mess, self.default_args),
            "Please provide an item name and optionally a system name: <item>[@system]"
        )

    def test_price_excessargs(self):
        self.assertEqual(
            self.price.price(self.default_mess, "item@system@excess"),
            "Please provide an item name and optionally a system name: <item>[@system]"
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_nosystem(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite"),
            self.price_template.format("Pyerite", "Jita", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_plex_nosystem(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Plex"),
            self.price_template.format("30 Day Pilot's License Extension (PLEX)",
                                       "Jita", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_system(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite@Amarr"),
            self.price_template.format("Pyerite", "Amarr", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_disambiguate(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Tritanium@Hek"),
            (self.price_template.format("Tritanium", "Hek", 45.99, 1000, 45.99, 1000, 0) +
             self.simple_disambiguate_template.format("items", "Tritanium",
                                                      "Alloyed Tritanium Bar") +
             self.simple_disambiguate_template.format("systems", "Hek", "Ghekon"))
        )

    def test_price_invaliditem(self):
        self.assertEqual(
            self.price.price(self.default_mess, "InvalidItem"),
            "Can't find a matching item"
        )

    def test_price_invalidsystem(self):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite@InvalidSystem"),
            "Can't find a matching system"
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", side_effect=APIError("TestException"))
    def test_price_APIError(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite"),
            "TestException"
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((0, 0), (0, 0)))
    def test_price_noorders(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite"),
            self.no_spread_template.format("Pyerite", "Jita", 0, 0, 0, 0)
        )

    def test_disambiguate_simple(self):
        self.assertEqual(
            self.price._disambiguate("Default", ["Test1", "Test2"], "Cat"),
            self.simple_disambiguate_template.format("Cat", "Default", "Test1, Test2")
        )

    def test_disambiguate_extended(self):
        self.assertEqual(
            self.price._disambiguate("Default", ["Test1", "Test2", "Test3", "Test4"], "Cat"),
            self.extended_disambiguate_template.format("Cat", "Default", "Test1, Test2, Test3", 1)
        )

    def test_get_market_orders(self):
        # The Forge
        regionID = 10000002
        # Tritanium
        item_typeID = 34

        res = self.price._get_market_orders(regionID, "Jita", item_typeID)
        self.assertIsInstance(res[0][0], float)
        self.assertIsInstance(res[0][1], (int, long))
        self.assertIsInstance(res[1][0], float)
        self.assertIsInstance(res[1][1], (int, long))

    @mock.patch("vmbot.helpers.api.get_crest_endpoint", return_value={'items': []})
    def test_get_market_orders_noorders(self, mock_crest):
        # The Forge
        regionID = 10000002
        # Pyerite
        item_typeID = 35

        res = self.price._get_market_orders(regionID, "Jita", item_typeID)
        self.assertEqual(res[0][0], 0)
        self.assertEqual(res[0][1], 0)
        self.assertEqual(res[1][0], 0)
        self.assertEqual(res[1][1], 0)


if __name__ == "__main__":
    unittest.main()
