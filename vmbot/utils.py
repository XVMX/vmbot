# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
from datetime import datetime
import cgi
import urllib
import xml.etree.ElementTree as ET
import sqlite3

import requests

from .botcmd import botcmd
from .helpers.files import STATICDATA_DB
from .helpers.exceptions import APIError
from .helpers import api, staticdata
from .helpers.format import format_affil, format_tickers, disambiguate
from .models import ISK

import config


class Price(object):
    @staticmethod
    def _get_market_orders(region, system, item):
        """Collect buy and sell order stats for item in system.

        Empty system name means data for all systems in region is collected.
        Output format: ((sell_price, sell_volume), (buy_price, buy_volume))
        """
        url = "https://crest-tq.eveonline.com/market/{}/orders/".format(region)
        type_ = "https://crest-tq.eveonline.com/inventory/types/{}/".format(item)

        res = api.request_rest(url, params={'type': type_}, timeout=5)

        sell = {'volume': 0, 'price': None}
        buy = {'volume': 0, 'price': None}

        for order in (order for order in res['items']
                      if order['location']['name'].startswith(system)):
            if order['buy']:
                buy['volume'] += order['volume']
                if buy['price'] is None or order['price'] > buy['price']:
                    buy['price'] = order['price']
            else:
                sell['volume'] += order['volume']
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

        # PLEX aliases
        if item.lower() in ("plex", "pilot license",
                            "pilot license extension",
                            "pilot's license extension"):
            item = "30 Day Pilot's License Extension (PLEX)"

        conn = sqlite3.connect(STATICDATA_DB)

        region = conn.execute(
            """SELECT regionID, regionName
               FROM mapRegions
               WHERE regionName LIKE :name;""",
            {'name': system_or_region}
        ).fetchone()

        # Sort by length of name so that the most similar system is first
        systems = conn.execute(
            """SELECT regionID, solarSystemName
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
            # Empty systemName matches every system in Price._get_market_orders
            regionID, market_name = region
            systemName = ""
        else:
            regionID, systemName = systems.pop(0)
            market_name = systemName

        try:
            orders = self._get_market_orders(regionID, systemName, typeID)
        except APIError as e:
            return unicode(e)

        (sell_price, sell_volume), (buy_price, buy_volume) = orders

        reply = ("<b>{}</b> in <b>{}</b>:<br />"
                 "Sells: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                 "Buys: <b>{:,.2f}</b> ISK -- {:,} units<br />"
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
        if len(args) == 2 and systems and systemName:
            reply += "<br />" + disambiguate(args[1], zip(*systems)[1], "systems")

        return reply


class EVEUtils(object):
    FEED_MIN_VAL = 5000000

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
            return reply + "<br />" + unicode(e)

        reply += "<br />Security status: <b>{:.2f}</b>".format(
            float(xml.find("securityStatus").text)
        )

        # /eve/CharacterInfo.xml.aspx returns corp history from latest to earliest
        corp_history = [row.attrib for row in reversed(xml.findall("rowset/row"))]
        num_records = len(corp_history)
        # Add endDate based on next startDate
        for i in xrange(num_records):
            corp_history[i]['endDate'] = (corp_history[i + 1]['startDate']
                                          if i + 1 < num_records else None)

        for record in corp_history[-10:]:
            corp_ticker, _ = api.get_tickers(int(record['corporationID']), None)
            reply += "<br />From {} til {} in <b>{} {}</b>".format(
                record['startDate'], record['endDate'] or "now",
                record['corporationName'], cgi.escape(format_tickers(corp_ticker, None))
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
            xml = api.request_xml("https://api.eveonline.com/server/ServerStatus.xml.aspx")
        except APIError:
            pass
        else:
            if xml.find("serverOpen").text == "True":
                reply += ". The server is online and {:,} players are playing.".format(
                    int(xml.find("onlinePlayers").text)
                )
            else:
                reply += ". The server is offline."

        return reply

    def km_feed(self):
        """Send a message to the primary chatroom with the latest losses."""
        if self.km_feed_id is None:
            try:
                self.km_feed_id = requests.get(
                    "https://zkillboard.com/api/losses/corporationID/2052404106/"
                    "limit/1/no-items/no-attackers/",
                    headers={'User-Agent': "XVMX JabberBot"}, timeout=3
                ).json()[0]['killID']
            except (requests.exceptions.RequestException, IndexError, ValueError):
                pass
            return

        url = "https://zkillboard.com/api/corporationID/2052404106/losses/"
        url += "afterKillID/{}/no-items/no-attackers/".format(self.km_feed_id)

        try:
            r = requests.get(url, headers={'User-Agent': "XVMX JabberBot"}, timeout=5)
        except requests.exceptions.RequestException:
            return
        if r.status_code != 200:
            return

        losses = filter(lambda x: x['zkb']['totalValue'] >= self.FEED_MIN_VAL, r.json())
        if not losses:
            return

        self.km_feed_id = losses[0]['killID']

        reply = "{} new loss(es):".format(len(losses))
        for loss in reversed(losses):
            victim = loss['victim']
            system = staticdata.solarSystemData(loss['solarSystemID'])

            reply += "<br/>{} {} | {} | {:.2f} ISK | {} ({}) | {} | {}".format(
                victim['characterName'] or victim['corporationName'],
                format_tickers("XVMX", "CONDI"), staticdata.typeName(victim['shipTypeID']),
                ISK(loss['zkb']['totalValue']),
                system['solarSystemName'], system['regionName'],
                loss['killTime'],
                "https://zkillboard.com/kill/{}/".format(loss['killID'])
            )

        self.send(config.JABBER['chatrooms'][0], reply, message_type="groupchat")

    def news_feed(self):
        """Send a message to the primary chatroom with the latest EVE news and devblogs."""

        def get_feed(type_):
            """Find all new Atom entries available at feedType.

            feedType must be either "news" or "devblog".
            """
            if type_ == "news":
                url = "http://newsfeed.eveonline.com/en-US/44/articles/page/1/20"
            elif type_ == "devblog":
                url = "http://newsfeed.eveonline.com/en-US/2/articles/page/1/20"
            else:
                raise ValueError('type_ must be either "news" or "devblog"')

            try:
                r = requests.get(url, headers={'User-Agent': "XVMX JabberBot"}, timeout=3)
            except requests.exceptions.RequestException as e:
                raise APIError("Error while connecting to Atom-Feed: {}".format(e))
            if r.status_code != 200:
                raise APIError("Atom-Feed returned error code {}".format(r.status_code))

            rss = ET.fromstring(r.content)
            ns = {'atom': "http://www.w3.org/2005/Atom", 'title': "http://ccp/custom",
                  'media': "http://search.yahoo.com/mrss/"}

            entries = [{'id': node.find("atom:id", ns).text,
                        'title': node.find("atom:title", ns).text,
                        'url': node.find("atom:link[@rel='alternate']", ns).attrib['href'],
                        'updated': node.find("atom:updated", ns).text}
                       for node in rss.findall("atom:entry", ns)]

            # ISO 8601 (eg 2016-02-10T16:35:32Z)
            entries.sort(key=lambda x: time.strptime(x['updated'], "%Y-%m-%dT%H:%M:%SZ"),
                         reverse=True)

            if self.news_feed_ids[type_] is None:
                self.news_feed_ids[type_] = entries[0]['id']
                return []
            else:
                idx = next(idx for idx, entry in enumerate(entries)
                           if entry['id'] == self.news_feed_ids[type_])
                self.news_feed_ids[type_] = entries[0]['id']
                return entries[:idx]

        news = None
        devblogs = None
        try:
            news = get_feed("news")
        except APIError:
            pass
        try:
            devblogs = get_feed("devblog")
        except APIError:
            pass

        if news:
            reply = "{} new EVE news:".format(len(news))
            for entry in news:
                reply += "<br /><b>{}</b>: {}".format(entry['title'], entry['url'])
            self.send(config.JABBER['chatrooms'][0], reply, message_type="groupchat")

        if devblogs:
            reply = "{} new devblog(s):".format(len(devblogs))
            for entry in devblogs:
                reply += "<br /><b>{}</b>: {}".format(entry['title'], entry['url'])
            self.send(config.JABBER['chatrooms'][0], reply, message_type="groupchat")

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
                results.append("{} is <b>{}</b>".format(character, res[0]['output']))

        return "<br />".join(results)
