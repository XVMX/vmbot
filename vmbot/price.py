# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import threading
import sqlite3

from concurrent import futures

from .botcmd import botcmd
from .helpers.files import STATICDATA_DB
from .helpers.exceptions import APIError, APIStatusError
from .helpers import api
from .helpers.sso import SSOToken
from .helpers import staticdata
from .helpers.format import disambiguate

import config


class Price(object):
    @staticmethod
    def _calc_totals(orders):
        """Extract pricing data from a list of orders."""
        sell_vol, sell_price = 0, None
        buy_vol, buy_price = 0, None

        for order in orders:
            if order['is_buy_order']:
                buy_vol += order['volume_remain']
                if buy_price is None or order['price'] > buy_price:
                    buy_price = order['price']
            else:
                sell_vol += order['volume_remain']
                if sell_price is None or order['price'] < sell_price:
                    sell_price = order['price']

        return (sell_price or 0, sell_vol), (buy_price or 0, buy_vol)

    @staticmethod
    def _get_region_orders(region_id, type_id):
        """Collect buy and sell order stats for item in region.

        Output format: ((sell_price, sell_volume), (buy_price, buy_volume))
        """
        params = {'page': 1, 'type_id': type_id}
        orders, head = api.request_esi("/v1/markets/{}/orders/", (region_id,),
                                       params=params, timeout=5, with_head=True)
        max_page = int(head.get('X-Pages', 1))

        while params['page'] < max_page:
            params['page'] += 1
            orders += api.request_esi("/v1/markets/{}/orders/", (region_id,),
                                      params=params, timeout=5)

        return Price._calc_totals(orders)

    @staticmethod
    def _get_system_orders(token, region_id, system_id, struct_ids, type_id):
        """Collect buy and sell order stats for item in system.

        Output format: ((sell_price, sell_volume), (buy_price, buy_volume))
        """
        if struct_ids and not {"esi-universe.read_structures.v1",
                               "esi-markets.structure_markets.v1"}.issubset(token.scopes):
            raise APIError("SSO token is missing required scopes")
        pool = futures.ThreadPoolExecutor(max_workers=10)

        # Filter valid locations
        sys_fut = pool.submit(api.request_esi, "/v4/universe/systems/{}/", (system_id,))
        struct_futs = []
        for id_ in struct_ids:
            f = pool.submit(token.request_esi, "/v2/universe/structures/{}/", (id_,))
            f.req_id = id_
            struct_futs.append(f)

        structs = set()
        for f in futures.as_completed(struct_futs):
            if f.result()['solar_system_id'] == system_id:
                structs.add(f.req_id)

        sys = sys_fut.result()
        stations = set(sys.get('stations', []))

        # Collect matching orders
        reg_fut = pool.submit(api.request_esi, "/v1/markets/{}/orders/", (region_id,),
                              params={'page': 1, 'type_id': type_id}, timeout=5, with_head=True)
        struct_futs = []
        for id_ in structs:
            f = pool.submit(token.request_esi, "/v1/markets/structures/{}/", (id_,),
                            params={'page': 1}, timeout=5, with_head=True)
            f.req_id = id_
            struct_futs.append(f)

        orders = []
        orders_lock = threading.Lock()

        def add_station_orders(f):
            with orders_lock:
                orders.extend(o for o in f.result() if o['location_id'] in stations)

        def add_struct_orders(f):
            with orders_lock:
                orders.extend(o for o in f.result() if o['type_id'] == type_id)

        order_futs = []
        for f in futures.as_completed(struct_futs):
            try:
                res, head = f.result()
            except APIStatusError as e:
                if e.status_code != 403:
                    raise e
                # 403/Market access denied (cannot be determined otherwise currently)
                continue
            with orders_lock:
                orders.extend(o for o in res if o['type_id'] == type_id)

            for p in range(2, int(head.get('X-Pages', 1)) + 1):
                page_f = pool.submit(token.request_esi, "/v1/markets/structures/{}/", (f.req_id,),
                                     params={'page': p}, timeout=5)
                page_f.add_done_callback(add_struct_orders)
                order_futs.append(page_f)

        res, head = reg_fut.result()
        with orders_lock:
                orders.extend(o for o in res if o['location_id'] in stations)

        for p in range(2, int(head.get('X-Pages', 1)) + 1):
            f = pool.submit(api.request_esi, "/v1/markets/{}/orders/", (region_id,),
                            params={'page': p, 'type_id': type_id}, timeout=5)
            f.add_done_callback(add_station_orders)
            order_futs.append(f)

        futures.wait(order_futs)
        return Price._calc_totals(orders)

    def _get_token(self):
        try:
            return self._token
        except AttributeError:
            self._token = SSOToken.from_refresh_token(config.SSO['refresh_token'])
            return self._token

    @botcmd
    def price(self, mess, args):
        """<item>[@system_or_region] - Price of item in system_or_region, defaulting to Jita"""
        args = [item.strip() for item in args.split('@')]
        if not 1 <= len(args) <= 2 or args[0] == "":
            return ("Please provide an item name and optionally a system/region name: "
                    "<item>[@system_or_region]")

        item = args[0]
        try:
            system_or_region = args[1]
        except IndexError:
            system_or_region = "Jita"

        token = self._get_token()
        params = {'search': system_or_region, 'categories': "region,solar_system"}
        try:
            if "esi-search.search_structures.v1" in token.scopes:
                params['categories'] += ",structure"
                res = token.request_esi("/v3/characters/{}/search/",
                                        (token.character_id,), params=params)
            else:
                res = api.request_esi("/v2/search/", params=params)
        except APIError as e:
            return unicode(e)

        region_id = res.get('region', [None])[0]
        system_ids = res.get('solar_system', [])
        struct_ids = res.get('structure', [])
        if region_id is None and not system_ids:
            return "Failed to find a matching system/region"

        # Sort by length of name so that the most similar item is first
        conn = sqlite3.connect(STATICDATA_DB)
        items = conn.execute(
            """SELECT typeID, typeName
               FROM invTypes
               WHERE typeName LIKE :name
                 AND marketGroupID IS NOT NULL
                 AND marketGroupID < 100000
               ORDER BY LENGTH(typeName) ASC;""",
            {'name': "%{}%".format(item)}
        ).fetchall()
        conn.close()

        if not items:
            return "Failed to find a matching item"

        type_id, type_name = items.pop(0)
        try:
            if region_id is not None:
                market_name = staticdata.region_data(region_id)['region_name']
                totals = self._get_region_orders(region_id, type_id)
            else:
                system_id = system_ids.pop(0)
                sys_data = staticdata.system_data(system_id)
                market_name = sys_data['system_name']
                totals = self._get_system_orders(token, sys_data['region_id'],
                                                 system_id, struct_ids, type_id)
        except APIError as e:
            return unicode(e)

        (sell_price, sell_volume), (buy_price, buy_volume) = totals

        reply = ("<strong>{}</strong> in <strong>{}</strong>:<br />"
                 "Sells: <strong>{:,.2f}</strong> ISK -- {:,} units<br />"
                 "Buys: <strong>{:,.2f}</strong> ISK -- {:,} units<br />"
                 "Spread: ").format(
            type_name, market_name, sell_price, sell_volume, buy_price, buy_volume
        )
        try:
            reply += "{:,.2%}".format((sell_price - buy_price) / sell_price)
        except ZeroDivisionError:
            # By request from Jack (See https://www.destroyallsoftware.com/talks/wat)
            reply += "NaNNaNNaNNaNNaNBatman!"

        if items:
            reply += "<br />" + disambiguate(args[0], zip(*items)[1], "items")
        if len(args) == 2 and system_ids and region_id is None:
            reply += "<br />" + disambiguate(
                args[1], [staticdata.system_data(id_)['system_name']
                          for id_ in system_ids], "systems"
            )

        return reply
