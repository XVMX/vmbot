# coding: utf-8

import time
from datetime import datetime, timedelta
import re
import urllib
import json
import xml.etree.ElementTree as ET
import sqlite3

import requests

from .botcmd import botcmd
from .config import config
from .helpers.files import STATICDATA_DB
from .helpers.exceptions import APIError
from .helpers import api
from .helpers import cache
from .helpers.regex import ZKB_REGEX
from .helpers.format import format_tickers
from .helpers.types import ISK


class Price(object):
    def _get_market_orders(self, region, system, item):
        url = "https://crest-tq.eveonline.com/market/{}/orders/".format(region)
        type_ = "https://crest-tq.eveonline.com/types/{}/".format(item)

        res = api.get_crest_endpoint(url, params={'type': type_}, timeout=5)

        sell = {'orders': [order for order in res['items'] if order['buy'] == False and
                           order['location']['name'].startswith(system)],
                'direction': max}
        buy = {'orders': [order for order in res['items'] if order['buy'] == True and
                          order['location']['name'].startswith(system)],
               'direction': min}

        for data in (sell, buy):
            data['volume'] = sum(order['volume'] for order in data['orders'])
            try:
                data['price'] = data['direction'](order['price'] for order in data['orders'])
            except ValueError:
                data['price'] = 0

        return (sell['price'], sell['volume']), (buy['price'], buy['volume'])

    def _disambiguate(self, given, like, category):
        reply = '<br />Other {} like "{}": {}'.format(category, given, ", ".join(like[:3]))

        if len(like) > 3:
            reply += ", and {} others".format(len(like) - 3)

        return reply

    @botcmd
    def price(self, mess, args):
        """<item>[@system] - Displays price of item in system, defaulting to Jita"""
        args = [item.strip() for item in args.split('@')]
        if not 1 <= len(args) <= 2 or args[0] == "":
            return "Please provide an item name and optionally a system name: <item>[@system]"

        item = args[0]
        try:
            system = args[1]
        except IndexError:
            system = "Jita"

        # PLEX aliases
        if item.lower() in ("plex", "pilot license",
                            "pilot license extension",
                            "pilot's license extension"):
            item = "30 Day Pilot's License Extension (PLEX)"

        conn = sqlite3.connect(STATICDATA_DB)

        systems = conn.execute(
            """SELECT regionID, solarSystemName
               FROM mapSolarSystems
               WHERE solarSystemName LIKE :name;""",
            {'name': "%{}%".format(system)}
        ).fetchall()
        if not systems:
            return "Can't find a matching system"

        items = conn.execute(
            """SELECT typeID, typeName
               FROM invTypes
               WHERE typeName LIKE :name
                 AND marketGroupID IS NOT NULL
                 AND marketGroupID < 100000;""",
            {'name': "%{}%".format(item)}
        ).fetchall()
        if not items:
            return "Can't find a matching item"

        conn.close()

        # Sort by length of name so that the most similar item is first
        items.sort(cmp=lambda x, y: cmp(len(x), len(y)), key=lambda x: x[1])
        systems.sort(cmp=lambda x, y: cmp(len(x), len(y)), key=lambda x: x[1])

        typeID, typeName = items.pop(0)
        regionID, systemName = systems.pop(0)
        typeName = typeName.encode("ascii", "replace")
        systemName = systemName.encode("ascii", "replace")

        try:
            orders = self._get_market_orders(regionID, systemName, typeID)
            sellprice, sellvolume = orders[0]
            buyprice, buyvolume = orders[1]
        except APIError as e:
            return str(e)

        reply = ("<b>{}</b> in <b>{}</b>:<br />"
                 "Sells: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                 "Buys: <b>{:,.2f}</b> ISK -- {:,} units<br />"
                 "Spread: ").format(
            typeName, systemName, sellprice, sellvolume, buyprice, buyvolume
        )
        try:
            reply += "{:,.2%}".format((sellprice - buyprice) / sellprice)
        except ZeroDivisionError:
            # By request from Jack (See https://www.destroyallsoftware.com/talks/wat)
            reply += "NaNNaNNaNNaNNaNBatman!"

        if items:
            reply += self._disambiguate(args[0], zip(*items)[1], "items")
        if len(args) == 2 and systems:
            reply += self._disambiguate(args[1], zip(*systems)[1], "systems")

        return reply


class EVEUtils(object):
    @botcmd
    def character(self, mess, args):
        """<character name>[, ...] - Displays employment information of character(s)"""
        if not args:
            return "Please provide character name(s), separated by commas"

        args = [item.strip() for item in args.split(',')]
        if len(args) > 10:
            return "Please limit your search to 10 characters at most"

        try:
            xml = api.post_xml_endpoint("https://api.eveonline.com/eve/CharacterID.xml.aspx",
                                        data={'names': ','.join(args)})
        except APIError as e:
            return str(e)

        charIDs = [int(character.attrib['characterID']) for character in xml[1][0]
                   if int(character.attrib['characterID'])]

        if not charIDs:
            return "None of these character(s) exist"

        try:
            xml = api.post_xml_endpoint(
                "https://api.eveonline.com/eve/CharacterAffiliation.xml.aspx",
                data={'ids': ','.join(map(str, charIDs))}, timeout=5
            )
        except APIError as e:
            return str(e)

        # Basic multi-character information
        descriptions = []
        for row in xml[1][0]:
            charName = row.attrib['characterName']
            corpName = row.attrib['corporationName']
            allianceName = row.attrib['allianceName']
            factionName = row.attrib['factionName']
            corp_ticker, alliance_ticker = api.get_tickers(int(row.attrib['corporationID']),
                                                           int(row.attrib['allianceID']))

            desc = "<b>{}</b> is part of corporation <b>{} {}</b>".format(
                charName, corpName, format_tickers(corp_ticker, None)
            )
            if allianceName:
                desc += " in <b>{} {}</b>".format(
                    allianceName, format_tickers(None, alliance_ticker)
                )
            if factionName:
                desc += " which is part of <b>{}</b>".format(factionName)

            descriptions.append(desc)

        reply = "<br />".join(descriptions)

        if len(charIDs) > 1:
            return reply

        # Detailed single-character information
        try:
            r = requests.get("http://evewho.com/api.php",
                             params={'type': "character", 'id': charIDs[0]},
                             headers={'User-Agent': "XVMX JabberBot"}, timeout=3)
        except requests.exceptions.RequestException as e:
            return "{}<br />Error while connecting to Eve Who-API: {}".format(reply, e)
        if r.status_code != 200:
            return "{}<br />Eve Who-API returned error code {}".format(reply, r.status_code)

        res = r.json()
        if res['info'] is None:
            return "{}<br />Failed to load data from Eve Who for this character".format(reply)

        reply += "<br />Security status: <b>{}</b>".format(res['info']['sec_status'])

        corpIDs = list({int(corp['corporation_id']) for corp in res['history'][-10:]})
        try:
            xml = api.post_xml_endpoint(
                "https://api.eveonline.com/eve/CharacterName.xml.aspx",
                data={'ids': ','.join(map(str, corpIDs))}
            )
        except APIError as e:
            return "{}<br/>Error while loading corp history: {}".format(reply, e)

        corps = {}
        for row in xml[1][0]:
            corpID = row.attrib['characterID']
            corp_ticker, alliance_ticker = api.get_tickers(corpID, None)
            corps[corpID] = {'corpName': row.attrib['name'], 'corp_ticker': corp_ticker}

        for record in res['history'][-10:]:
            data = corps[record['corporation_id']]
            reply += "<br />From {} til {} in <b>{} {}</b>".format(
                record['start_date'],
                record['end_date'] or "now",
                data['corpName'],
                format_tickers(data['corp_ticker'], None)
            )

        if len(res['history']) > 10:
            reply += "<br/>The full history is available at http://evewho.com/pilot/{}/".format(
                urllib.quote(res['info']['name'])
            )

        return reply

    @botcmd
    def evetime(self, mess, args):
        """[+offset] - Displays the current evetime, server status and evetime + offset if given"""
        evetime = datetime.utcnow()
        reply = "The current EVE time is {:%Y-%m-%d %H:%M:%S}".format(evetime)

        try:
            args = int(args)
            offset_time = evetime + timedelta(hours=args)
            reply += " and {:+} hour(s) is {:%Y-%m-%d %H:%M:%S}".format(args, offset_time)
        except ValueError:
            pass

        try:
            xml = api.post_xml_endpoint("https://api.eveonline.com/server/ServerStatus.xml.aspx")
            if xml[1][0].text == "True":
                reply += "\nThe server is online and {} players are playing".format(xml[1][1].text)
            else:
                reply += "\nThe server is offline"
        except APIError:
            pass

        return reply

    @botcmd
    def zbot(self, mess, args, compact=False):
        """<zKB link> - Displays statistics of a killmail"""
        args = args.strip().split(' ', 1)

        regex = ZKB_REGEX.match(args[0])
        if regex is None:
            return "Please provide a link to a zKB killmail"

        killID = regex.group(1)

        url = "https://zkillboard.com/api/killID/{}/no-items/".format(killID)
        cached = cache.get_http(url)
        if not cached:
            try:
                r = requests.get(url, headers={'User-Agent': "XVMX JabberBot"}, timeout=5)
            except requests.exceptions.RequestException as e:
                return "Error while connecting to zKB-API: {}".format(e)
            if r.status_code != 200:
                return "zKB-API returned error code {}".format(r.status_code)

            killdata = r.json()
            try:
                expires_in = int(re.search("max-age=(\d+)", r.headers['Cache-Control']).group(1))
            except (KeyError, AttributeError):
                expires_in = 0
            cache.set_http(url, doc=r.content, expiry=int(time.time() + expires_in))
        else:
            killdata = json.loads(cached)

        if not killdata:
            return "Failed to load data for {}".format(regex.group(0))

        victim = killdata[0]['victim']
        system = api.get_solarSystemData(killdata[0]['solarSystemID'])
        attackers = killdata[0]['attackers']
        corp_ticker, alliance_ticker = api.get_tickers(victim['corporationID'],
                                                       victim['allianceID'])

        reply = "{} {} | {} | {:.2f} ISK | {} ({}) | {} participants | {}".format(
            victim['characterName'] or victim['corporationName'],
            format_tickers(corp_ticker, alliance_ticker), api.get_typeName(victim['shipTypeID']),
            ISK(killdata[0]['zkb']['totalValue']),
            system['solarSystemName'], system['regionName'],
            len(attackers),
            killdata[0]['killTime']
        )

        if compact:
            return reply

        if victim['characterName']:
            reply += "<br /><b>{}</b> is part of corporation <b>{} {}</b>".format(
                victim['characterName'], victim['corporationName'],
                format_tickers(corp_ticker, None)
            )
        else:
            reply += "<br />The structure is owned by corporation <b>{} {}</b>".format(
                victim['corporationName'], format_tickers(corp_ticker, None)
            )
        if victim['allianceName']:
            reply += " in <b>{} {}</b>".format(victim['allianceName'],
                                               format_tickers(None, alliance_ticker))
        if victim['factionName']:
            reply += " which is part of <b>{}</b>".format(victim['factionName'])

        reply += " and took <b>{:,} damage</b> for <b>{:,} point(s)</b>".format(
            victim['damageTaken'], killdata[0]['zkb']['points']
        )

        attackers = [{'characterName': char['characterName'],
                      'corporationID': char['corporationID'],
                      'corporationName': char['corporationName'],
                      'damageDone': char['damageDone'],
                      'shipTypeName': api.get_typeName(char['shipTypeID']),
                      'finalBlow': bool(char['finalBlow'])} for char in attackers]
        # Sort after inflicted damage
        attackers.sort(key=lambda x: x['damageDone'], reverse=True)

        # Add attackerDetails
        attacker_info = "<b>{}</b> {} (<b>{}</b>) inflicted <b>{:,} damage</b> "
        attacker_info += "(<i>{:,.2%} of total damage</i>)"
        for char in attackers[:5]:
            corp_ticker, alliance_ticker = api.get_tickers(char['corporationID'], None)

            reply += "<br />"
            reply += attacker_info.format(char['characterName'] or char['corporationName'],
                                          format_tickers(corp_ticker, alliance_ticker),
                                          char['shipTypeName'], char['damageDone'],
                                          char['damageDone'] / float(victim['damageTaken']))
            reply += " and scored the <b>final blow</b>" if char['finalBlow'] else ""

        # Add final blow if not already included
        if "final blow" not in reply:
            char = next(char for char in attackers if char['finalBlow'])
            corp_ticker, alliance_ticker = api.get_tickers(char['corporationID'], None)

            reply += "<br />"
            reply += attacker_info.format(char['characterName'] or char['corporationName'],
                                          format_tickers(corp_ticker, alliance_ticker),
                                          char['shipTypeName'], char['damageDone'],
                                          char['damageDone'] / float(victim['damageTaken']))
            reply += " and scored the <b>final blow</b>"

        return reply

    def km_feed(self):
        """Send a message to the first chatroom with the latest losses."""
        url = "https://zkillboard.com/api/corporationID/2052404106/losses/"
        url += "afterKillID/{}/no-items/no-attackers/".format(self.km_feed_id)

        try:
            r = requests.get(url, headers={'User-Agent': "XVMX JabberBot"}, timeout=5)
        except requests.exceptions.RequestException:
            return
        if r.status_code != 200:
            return

        min_val = 5000000
        losses = filter(lambda x: x['zkb']['totalValue'] >= min_val, r.json())
        if not losses:
            return

        self.km_feed_id = losses[0]['killID']

        reply = "{} new loss(es):".format(len(losses))
        for loss in reversed(losses):
            victim = loss['victim']
            system = api.get_solarSystemData(loss['solarSystemID'])

            reply += "<br/>{} {} | {} | {:.2f} ISK | {} ({}) | {} | {}".format(
                victim['characterName'] or victim['corporationName'],
                format_tickers("XVMX", "CONDI"), api.get_typeName(victim['shipTypeID']),
                ISK(loss['zkb']['totalValue']),
                system['solarSystemName'], system['regionName'],
                loss['killTime'],
                "https://zkillboard.com/kill/{}/".format(loss['killID'])
            )

        self.send(config['jabber']['chatrooms'][0], reply, message_type="groupchat")

    def news_feed(self):
        """Send a message to the first chatroom with the latest EVE news and devblogs."""
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
            self.send(config['jabber']['chatrooms'][0], reply, message_type="groupchat")

        if devblogs:
            reply = "{} new devblog(s):".format(len(devblogs))
            for entry in devblogs:
                reply += "<br /><b>{}</b>: {}".format(entry['title'], entry['url'])
            self.send(config['jabber']['chatrooms'][0], reply, message_type="groupchat")

    @botcmd
    def rcbl(self, mess, args):
        """<name>[, ...] - Displays if name has an entry in the blacklist"""
        url = "{}{}/".format(config['blacklist']['url'], config['blacklist']['key'])
        results = []

        for character in (item.strip() for item in args.split(',')):
            try:
                r = requests.get(url + character, headers={'User-Agent': "XVMX JabberBot"},
                                 timeout=3)
                results.append("{} is <b>{}</b>".format(character, r.json()[0]['output']))
            except requests.exceptions.RequestException:
                results.append("Failed to load blacklist entry for {}".format(character))

        return "<br />".join(results)
