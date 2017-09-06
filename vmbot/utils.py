# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta
import urllib
import json
import sqlite3

from .botcmd import botcmd
from .helpers.files import STATICDATA_DB
from .helpers.exceptions import APIError, APIStatusError
from .helpers import api
from .helpers import staticdata
from .helpers.format import format_affil, format_tickers, disambiguate

import config


class Price(object):
    @staticmethod
    def _get_market_orders(regionID, systemID, typeID):
        """Collect buy and sell order stats for item in system.

        If systemID is None, data for all systems in region will be collected.
        Output format: ((sell_price, sell_volume), (buy_price, buy_volume))
        """
        # Get valid locations
        locs = set()
        if systemID is not None:
            sys = api.request_esi("/v3/universe/systems/{}/", (systemID,))
            locs.update(sys.get('stations', []))

        # Collect matching orders
        params = {'page': 1, 'type_id': typeID}
        res, head = api.request_esi("/v1/markets/{}/orders/", (regionID,),
                                    params=params, with_head=True)
        orders = [o for o in res if systemID is None or o['location_id'] in locs]
        max_page = int(head.get('X-Pages', 1))

        while params['page'] < max_page:
            params['page'] += 1
            res = api.request_esi("/v1/markets/{}/orders/", (regionID,), params=params)
            orders.extend(o for o in res if systemID is None or o['location_id'] in locs)

        sell = {'volume': 0, 'price': None}
        buy = {'volume': 0, 'price': None}

        for order in orders:
            if order['is_buy_order']:
                buy['volume'] += order['volume_remain']
                if buy['price'] is None or order['price'] > buy['price']:
                    buy['price'] = order['price']
            else:
                sell['volume'] += order['volume_remain']
                if sell['price'] is None or order['price'] < sell['price']:
                    sell['price'] = order['price']

        return (sell['price'] or 0, sell['volume']), (buy['price'] or 0, buy['volume'])

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

        conn = sqlite3.connect(STATICDATA_DB)

        region = conn.execute(
            """SELECT regionID, regionName
               FROM mapRegions
               WHERE regionName LIKE :name;""",
            {'name': system_or_region}
        ).fetchone()

        # Sort by length of name so that the most similar system is first
        systems = conn.execute(
            """SELECT regionID, solarSystemID, solarSystemName
               FROM mapSolarSystems
               WHERE solarSystemName LIKE :name
               ORDER BY LENGTH(solarSystemName) ASC;""",
            {'name': "%{}%".format(system_or_region)}
        ).fetchall()
        if not systems and not region:
            return "Failed to find a matching system/region"

        # Sort by length of name so that the most similar item is first
        items = conn.execute(
            """SELECT typeID, typeName
               FROM invTypes
               WHERE typeName LIKE :name
                 AND marketGroupID IS NOT NULL
                 AND marketGroupID < 100000
               ORDER BY LENGTH(typeName) ASC;""",
            {'name': "%{}%".format(item)}
        ).fetchall()
        if not items:
            return "Failed to find a matching item"

        conn.close()

        typeID, typeName = items.pop(0)
        if region:
            # Price._get_market_orders returns regional data if systemID is None
            regionID, market_name = region
            systemID = None
        else:
            regionID, systemID, market_name = systems.pop(0)

        try:
            orders = self._get_market_orders(regionID, systemID, typeID)
        except APIError as e:
            return unicode(e)

        (sell_price, sell_volume), (buy_price, buy_volume) = orders

        reply = ("<strong>{}</strong> in <strong>{}</strong>:<br />"
                 "Sells: <strong>{:,.2f}</strong> ISK -- {:,} units<br />"
                 "Buys: <strong>{:,.2f}</strong> ISK -- {:,} units<br />"
                 "Spread: ").format(
            typeName, market_name, sell_price, sell_volume, buy_price, buy_volume
        )
        try:
            reply += "{:,.2%}".format((sell_price - buy_price) / sell_price)
        except ZeroDivisionError:
            # By request from Jack (See https://www.destroyallsoftware.com/talks/wat)
            reply += "NaNNaNNaNNaNNaNBatman!"

        if items:
            reply += "<br />" + disambiguate(args[0], zip(*items)[1], "items")
        if len(args) == 2 and systems and systemID:
            reply += "<br />" + disambiguate(args[1], zip(*systems)[2], "systems")

        return reply


class EVEUtils(object):
    @botcmd
    def character(self, mess, args):
        """<character> - Employment information for a single character"""
        args = args.strip()
        if not args:
            return "Please provide a character name"

        params = {'search': args, 'categories': "character", 'strict': "true"}
        try:
            res = api.request_esi("/v1/search/", params=params)
            char_id = res['character'][0]
        except APIError as e:
            return unicode(e)
        except KeyError:
            return "This character doesn't exist"

        # Load character data
        try:
            data = api.request_esi("/v4/characters/{}/", (char_id,))
        except APIError as e:
            return unicode(e)

        faction_id = None
        payload = json.dumps([char_id])
        try:
            affil = api.request_esi("/v1/characters/affiliation/", data=payload, method="POST")[0]
            faction_id = affil.get('faction_id', None)
        except APIError:
            pass

        corp_hist = []
        try:
            corp_hist = api.request_esi("/v1/characters/{}/corporationhistory/", (char_id,))
        except APIError:
            pass

        # Process corporation history
        num_recs = len(corp_hist)
        corp_hist.sort(key=lambda x: x['record_id'])
        for i in reversed(xrange(num_recs)):
            rec = corp_hist[i]
            rec['start_date'] = datetime.strptime(rec['start_date'], "%Y-%m-%dT%H:%M:%SZ")
            rec['end_date'] = corp_hist[i + 1]['start_date'] if i + 1 < num_recs else None

        # Show all entries from the last 5 years (min 10) or the 25 most recent entries
        min_age = datetime.utcnow() - timedelta(days=5 * 365)
        max_hist = max(-25, -len(corp_hist))
        while max_hist < -10 and corp_hist[max_hist + 1]['start_date'] < min_age:
            max_hist += 1
        corp_hist = corp_hist[max_hist:]

        # Load corporation data
        corp_ids = {data['corporation_id']}
        corp_ids.update(rec['corporation_id'] for rec in corp_hist)

        corps = {}
        ally_hist = {}
        for id_ in corp_ids:
            try:
                corps[id_] = api.request_esi("/v3/corporations/{}/", (id_,))
            except APIError:
                corps[id_] = {'corporation_name': "ERROR", 'ticker': "ERROR"}

            try:
                ally_hist[id_] = api.request_esi("/v2/corporations/{}/alliancehistory/", (id_,))
                ally_hist[id_].sort(key=lambda x: x['record_id'])
            except APIError:
                ally_hist[id_] = []

        # Corporation Alliance history
        ally_ids = {data['alliance_id']} if 'alliance_id' in data else set()
        for rec in corp_hist:
            hist = ally_hist[rec['corporation_id']]
            date_hist = [datetime.strptime(ally['start_date'], "%Y-%m-%dT%H:%M:%SZ")
                         for ally in hist]
            start_date = rec['start_date']
            end_date = rec['end_date'] or datetime.utcnow()

            j, k = 0, len(date_hist) - 1
            while j <= k:
                if date_hist[j] <= start_date:
                    j += 1
                elif date_hist[k] >= end_date:
                    k -= 1
                else:
                    break
            j = max(0, j - 1)
            k = min(len(date_hist), k + 1)

            rec['alliances'] = [ent['alliance_id'] for ent in hist[j:k] if 'alliance_id' in ent]
            ally_ids.update(rec['alliances'])

        # Load alliance data
        allys = {}
        for id_ in ally_ids:
            try:
                allys[id_] = api.request_esi("/v2/alliances/{}/", (id_,))
            except APIError:
                allys[id_] = {'alliance_name': "ERROR", 'ticker': "ERROR"}

        # Format output
        corp = corps[data['corporation_id']]
        ally = allys[data['alliance_id']] if 'alliance_id' in data else {}
        fac_name = staticdata.faction_name(faction_id) if faction_id is not None else None

        reply = format_affil(data['name'], data.get('security_status', 0),
                             corp['corporation_name'], ally.get('alliance_name', None),
                             fac_name, corp['ticker'], ally.get('ticker', None))

        for rec in corp_hist:
            end = ("{:%Y-%m-%d %H:%M:%S}".format(rec['end_date'])
                   if rec['end_date'] is not None else "now")
            corp = corps[rec['corporation_id']]
            corp_ticker = corp['ticker']
            ally_ticker = "</strong>/<strong>".join(
                format_tickers(None, allys[id_]['ticker'], html=True) for id_ in rec['alliances']
            )
            ally_ticker = " " + ally_ticker if ally_ticker else ""

            reply += "<br />From {:%Y-%m-%d %H:%M:%S} til {} in <strong>{} {}{}</strong>".format(
                rec['start_date'], end, corp['corporation_name'],
                format_tickers(corp_ticker, None, html=True), ally_ticker
            )

        if len(corp_hist) < num_recs:
            reply += "<br />The full history is available at https://evewho.com/pilot/{}/".format(
                urllib.quote_plus(data['name'])
            )

        return reply

    @botcmd
    def evetime(self, mess, args):
        """Current EVE time and server status"""
        reply = "The current EVE time is {:%Y-%m-%d %H:%M:%S}".format(datetime.utcnow())

        try:
            stat = api.request_esi("/v1/status/")
        except APIStatusError:
            reply += ". The server is offline."
        except APIError:
            pass
        else:
            reply += ". The server is online"
            if stat.get('vip', False):
                reply += " (VIP mode)"
            reply += " and {:,} players are playing.".format(stat['players'])

        return reply

    @botcmd
    def rcbl(self, mess, args):
        """<character>[, ...] - Blacklist status of character(s)"""
        url = config.BLACKLIST['url'] + config.BLACKLIST['key'] + '/'
        results = []

        for character in (item.strip() for item in args.split(',')):
            try:
                res = api.request_rest(url + character)
            except APIError:
                results.append("Failed to load blacklist entry for " + character)
            else:
                results.append("{} is <strong>{}</strong>".format(character, res[0]['output']))

        return "<br />".join(results)
