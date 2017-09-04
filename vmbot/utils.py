# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime
import cgi
import urllib
import sqlite3

from .botcmd import botcmd
from .helpers.files import STATICDATA_DB
from .helpers.exceptions import APIError, APIStatusError
from .helpers import api
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
        """<character>[, ...] - Employment information of character(s)"""
        if not args:
            return "Please provide character name(s), separated by commas"

        args = [item.strip() for item in args.split(',')]
        if len(args) > 10:
            return "Please limit your search to 10 characters at once"

        try:
            xml = api.request_xml("https://api.eveonline.com/eve/CharacterID.xml.aspx",
                                  params={'names': ','.join(args)}).find("rowset")
        except APIError as e:
            return unicode(e)

        charIDs = [int(character.attrib['characterID']) for character in xml
                   if int(character.attrib['characterID'])]

        if not charIDs:
            return "None of these character(s) exist"

        try:
            xml = api.request_xml(
                "https://api.eveonline.com/eve/CharacterAffiliation.xml.aspx",
                params={'ids': ','.join(map(unicode, charIDs))}, timeout=5
            ).find("rowset")
        except APIError as e:
            return unicode(e)

        # Basic multi-character information
        descriptions = []
        for row in xml:
            characterName = row.attrib['characterName']
            corporationName = row.attrib['corporationName']
            allianceName = row.attrib['allianceName']
            factionName = row.attrib['factionName']
            corp_ticker, alliance_ticker = api.get_tickers(int(row.attrib['corporationID']),
                                                           int(row.attrib['allianceID']))

            descriptions.append(format_affil(characterName, corporationName, allianceName,
                                             factionName, corp_ticker, alliance_ticker))

        reply = "<br />".join(descriptions)

        if len(charIDs) > 1:
            return reply

        # Detailed single-character information
        try:
            xml = api.request_xml("https://api.eveonline.com/eve/CharacterInfo.xml.aspx",
                                  params={'characterID': charIDs[0]})
        except APIError as e:
            return "{}<br />{}".format(reply, e)

        reply += "<br />Security status: <strong>{:.2f}</strong>".format(
            float(xml.find("securityStatus").text)
        )

        # /eve/CharacterInfo.xml.aspx returns corp history from latest to earliest
        corp_history = [row.attrib for row in reversed(xml.findall("rowset/row"))]
        num_records = len(corp_history)
        # Add endDate based on next startDate
        for i in xrange(num_records):
            corp_history[i]['endDate'] = (corp_history[i + 1]['startDate']
                                          if i + 1 < num_records else None)
        corp_history = corp_history[-10:]

        # Corporation Alliance history
        ally_hist = {}
        for corp in {rec['corporationID'] for rec in corp_history}:
            try:
                hist = api.request_rest(
                    "https://esi.tech.ccp.is/latest/corporations/{}/alliancehistory/".format(corp),
                    params={'datasource': "tranquility"}
                )
            except APIError:
                ally_hist[corp] = []
                continue
            hist.sort(key=lambda x: x['record_id'])
            ally_hist[corp] = hist

        for i in xrange(len(corp_history)):
            record = corp_history[i]
            hist = ally_hist[record['corporationID']]
            date_hist = [datetime.strptime(ally['start_date'], "%Y-%m-%dT%H:%M:%SZ")
                         for ally in hist]
            start_date = datetime.strptime(record['startDate'], "%Y-%m-%d %H:%M:%S")
            end_date = (datetime.strptime(record['endDate'], "%Y-%m-%d %H:%M:%S")
                        if record['endDate'] is not None else datetime.utcnow())

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

            allyIDs = [rec['alliance_id'] for rec in hist[j:k] if 'alliance_id' in rec]
            ally_tickers = {_id: api.get_tickers(None, _id)[1] for _id in set(allyIDs)}
            corp_history[i]['alliances'] = [ally_tickers[_id] for _id in allyIDs]

        for record in corp_history:
            corp_ticker, _ = api.get_tickers(int(record['corporationID']), None)
            ally_ticker = "</strong>/<strong>".join(cgi.escape(format_tickers(None, ticker))
                                                    for ticker in record['alliances'])
            reply += "<br />From {} til {} in <strong>{} {}{}</strong>".format(
                record['startDate'], record['endDate'] or "now",
                record['corporationName'], cgi.escape(format_tickers(corp_ticker, None)),
                (" " + ally_ticker if ally_ticker else "")
            )

        if num_records > 10:
            reply += "<br />The full history is available at https://evewho.com/pilot/{}/".format(
                urllib.quote_plus(xml.find("characterName").text)
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
