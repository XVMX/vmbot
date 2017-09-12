# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import os

from vmbot.helpers.files import BOT_DB
from vmbot.helpers.exceptions import APIError
import vmbot.helpers.database as db

from vmbot.utils import Price


class TestPrice(unittest.TestCase):
    default_mess = ""
    default_args = ""

    price_template = ("<strong>{}</strong> in <strong>{}</strong>:<br />"
                      "Sells: <strong>{:,.2f}</strong> ISK -- {:,} units<br />"
                      "Buys: <strong>{:,.2f}</strong> ISK -- {:,} units<br />"
                      "Spread: {:,.2%}")
    no_spread_template = ("<strong>{}</strong> in <strong>{}</strong>:<br />"
                          "Sells: <strong>{:,.2f}</strong> ISK -- {:,} units<br />"
                          "Buys: <strong>{:,.2f}</strong> ISK -- {:,} units<br />"
                          "Spread: NaNNaNNaNNaNNaNBatman!")

    def setUp(self):
        self.price = Price()

    def tearDown(self):
        del self.price

    @classmethod
    def setUpClass(cls):
        try:
            os.remove(BOT_DB)
        except OSError:
            pass
        else:
            db.init_db()

    @classmethod
    def tearDownClass(cls):
        return cls.setUpClass()

    def test_price_noargs(self):
        self.assertEqual(
            self.price.price(self.default_mess, self.default_args),
            ("Please provide an item name and optionally a system/region name: "
             "<item>[@system_or_region]")
        )

    def test_price_excessargs(self):
        self.assertEqual(
            self.price.price(self.default_mess, "item@system@excess"),
            ("Please provide an item name and optionally a system/region name: "
             "<item>[@system_or_region]")
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_nosystem(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite"),
            self.price_template.format("Pyerite", "Jita", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_system(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite@Amarr"),
            self.price_template.format("Pyerite", "Amarr", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_region(self, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Mexallon@The Forge"),
            self.price_template.format("Mexallon", "The Forge", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_market_orders", return_value=((45.99, 1000), (45.99, 1000)))
    @mock.patch("vmbot.utils.disambiguate", return_value="TestResponse")
    def test_price_disambiguate(self, mock_disambiguate, mock_price_volume):
        self.assertEqual(
            self.price.price(self.default_mess, "Tritanium@Hek"),
            (self.price_template.format("Tritanium", "Hek", 45.99, 1000, 45.99, 1000, 0) +
             "<br />TestResponse" + "<br />TestResponse")
        )

    def test_price_invaliditem(self):
        self.assertEqual(
            self.price.price(self.default_mess, "InvalidItem"),
            "Failed to find a matching item"
        )

    def test_price_invalidsystem(self):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite@InvalidSystem"),
            "Failed to find a matching system/region"
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

    def test_get_market_orders(self):
        # The Forge
        regionID = 10000002
        # Jita
        systemID = 30000142
        # Tritanium
        item_typeID = 34

        # Regional data
        res_r = Price._get_market_orders(regionID, None, item_typeID)
        self.assertIsInstance(res_r[0][0], float)
        self.assertIsInstance(res_r[0][1], (int, long))
        self.assertIsInstance(res_r[1][0], float)
        self.assertIsInstance(res_r[1][1], (int, long))

        # System data
        res_s = Price._get_market_orders(regionID, systemID, item_typeID)
        self.assertGreaterEqual(res_s[0][0], res_r[0][0])
        self.assertLessEqual(res_s[0][1], res_r[0][1])
        self.assertLessEqual(res_s[1][0], res_r[1][0])
        self.assertLessEqual(res_s[1][1], res_r[1][1])

    @mock.patch("vmbot.helpers.api.request_esi", return_value=([], {}))
    def test_get_market_orders_noorders(self, mock_esi):
        # The Forge
        regionID = 10000002
        # Pyerite
        item_typeID = 35

        res = Price._get_market_orders(regionID, None, item_typeID)
        self.assertEqual(res[0][0], 0)
        self.assertEqual(res[0][1], 0)
        self.assertEqual(res[1][0], 0)
        self.assertEqual(res[1][1], 0)

    @mock.patch("vmbot.helpers.api.request_esi", side_effect=[([], {'X-Pages': 2}), []])
    def test_get_market_orders_paginated(self, mock_esi):
        # The Forge
        regionID = 10000002
        # Mexallon
        item_typeID = 36

        res = Price._get_market_orders(regionID, None, item_typeID)
        self.assertEqual(res[0][0], 0)
        self.assertEqual(res[0][1], 0)
        self.assertEqual(res[1][0], 0)
        self.assertEqual(res[1][1], 0)


if __name__ == "__main__":
    unittest.main()
