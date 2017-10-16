# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import os

from vmbot.helpers.files import BOT_DB
from vmbot.helpers.exceptions import APIError
import vmbot.helpers.database as db

from vmbot.utils import Price


def token_reg():
    class Obj(object):
        scopes = []
    return Obj()


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

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    @mock.patch("vmbot.utils.Price._get_system_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_nosystem(self, mock_system_orders, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite"),
            self.price_template.format("Pyerite", "Jita", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    @mock.patch("vmbot.utils.Price._get_system_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_system(self, mock_system_orders, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite@Amarr"),
            self.price_template.format("Pyerite", "Amarr", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    @mock.patch("vmbot.utils.Price._get_region_orders", return_value=((45.99, 1000), (45.99, 1000)))
    def test_price_region(self, mock_region_orders, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "Mexallon@The Forge"),
            self.price_template.format("Mexallon", "The Forge", 45.99, 1000, 45.99, 1000, 0)
        )

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    @mock.patch("vmbot.utils.Price._get_system_orders", return_value=((45.99, 1000), (45.99, 1000)))
    @mock.patch("vmbot.utils.disambiguate", return_value="TestResponse")
    def test_price_disambiguate(self, mock_disambiguate, mock_system_orders, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "Tritanium@ika"),
            (self.price_template.format("Tritanium", "Ikami", 45.99, 1000, 45.99, 1000, 0) +
             "<br />TestResponse" + "<br />TestResponse")
        )

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    def test_price_invaliditem(self, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "InvalidItem"),
            "Failed to find a matching item"
        )

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    def test_price_invalidsystem(self, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite@InvalidSystem"),
            "Failed to find a matching system/region"
        )

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    @mock.patch("vmbot.helpers.api.request_esi", side_effect=APIError("TestException"))
    def test_price_searcherror(self, mock_esi, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "Mexallon"),
            "TestException"
        )

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    @mock.patch("vmbot.utils.Price._get_system_orders", side_effect=APIError("TestException"))
    def test_price_orderserror(self, mock_system_orders, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite"),
            "TestException"
        )

    @mock.patch("vmbot.utils.Price._get_token", side_effect=token_reg)
    @mock.patch("vmbot.utils.Price._get_system_orders", return_value=((0, 0), (0, 0)))
    def test_price_noorders(self, mock_system_orders, mock_token):
        self.assertEqual(
            self.price.price(self.default_mess, "Pyerite"),
            self.no_spread_template.format("Pyerite", "Jita", 0, 0, 0, 0)
        )

    @mock.patch("vmbot.helpers.sso.SSOToken.from_refresh_token", return_value=object())
    def test_get_token(self, mock_sso):
        tk = self.price._get_token()
        self.assertIs(self.price._get_token(), tk)

    def test_calc_totals(self):
        orders = [
            {'is_buy_order': False, 'volume_remain': 674, 'price': 63.61},
            {'is_buy_order': False, 'volume_remain': 26, 'price': 56.00},
            {'is_buy_order': True, 'volume_remain': 500, 'price': 42.33},
        ]
        self.assertTupleEqual(self.price._calc_totals(orders), ((56.00, 700), (42.33, 500)))

    def test_calc_totals_noorders(self):
        self.assertTupleEqual(self.price._calc_totals([]), ((0, 0), (0, 0)))

    def test_get_region_orders(self):
        # The Forge
        region_id = 10000002
        # Tritanium
        type_id = 34

        res_r = Price._get_region_orders(region_id, type_id)
        self.assertIsInstance(res_r[0][0], float)
        self.assertIsInstance(res_r[0][1], (int, long))
        self.assertIsInstance(res_r[1][0], float)
        self.assertIsInstance(res_r[1][1], (int, long))

    @mock.patch("vmbot.helpers.api.request_esi", side_effect=[([], {'X-Pages': 2}), []])
    def test_get_region_orders_paginated(self, mock_esi):
        # The Forge
        region_id = 10000002
        # Mexallon
        type_id = 36

        res = Price._get_region_orders(region_id, type_id)
        self.assertEqual(res[0][0], 0)
        self.assertEqual(res[0][1], 0)
        self.assertEqual(res[1][0], 0)
        self.assertEqual(res[1][1], 0)


if __name__ == "__main__":
    unittest.main()
