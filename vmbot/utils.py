from jabberbot import botcmd

import time
from datetime import datetime, timedelta
from calendar import timegm
from os import path
import json
import xml.etree.ElementTree as ET
import sqlite3

import requests

from vmbot_config import config as vmc


STATICDATA = path.join(path.dirname(__file__), "data", "staticdata.sqlite")
APICACHE = path.join(path.dirname(__file__), "data", "api.cache")


class ISK(float):
    """Represent ISK values."""
    def __format__(self, format_spec):
        """Format the ISK value with commonly used prefixes."""
        for unit in ['', 'k', 'm', 'b']:
            if self < 1000:
                return "{}{}".format(format(self, format_spec), unit)
            self /= 1000
        return "{}t".format(format(self, format_spec))


class PriceError(StandardError):
    pass


class Price(object):
    def getPriceVolume(self, orderType, region, system, item):
        url = "https://public-crest.eveonline.com/market/{}/orders/{}/".format(region, orderType)
        url += "?type=https://public-crest.eveonline.com/types/{}/".format(item)

        try:
            r = requests.get(url, headers={'User-Agent': "XVMX JabberBot"}, timeout=5)
        except requests.exceptions.RequestException as e:
            raise PriceError("Error while connecting to CREST: {}".format(e))
        if r.status_code != 200:
            raise PriceError("CREST returned error code {}".format(r.status_code))

        res = r.json()

        orders = [order for order in res['items'] if order['location']['name'].startswith(system)]
        volume = sum([order['volume'] for order in orders])
        direction = min if orderType == "sell" else max
        try:
            price = direction([order['price'] for order in orders])
        except ValueError:
            price = 0

        return (volume, price)

    def disambiguate(self, given, like, category):
        reply = '<br />Other {} like "{}": {}'.format(category, given, ", ".join(like[:3]))
        if len(like) > 3:
            reply += ", and {} others".format(len(like) - 3)
        return reply

    @botcmd
    def price(self, mess, args):
        """<item>@[system] - Displays price of item in system, defaulting to Jita"""
        args = [item.strip() for item in args.split('@')]
        if len(args) not in (1, 2) or args[0] == "":
            return "Please provide an item name and optionally a system name: <item>@[system]"

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

        conn = sqlite3.connect(STATICDATA)
        conn.text_factory = lambda t: unicode(t, "utf-8", "replace")

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
            sellvolume, sellprice = self.getPriceVolume("sell", regionID, systemName, typeID)
            buyvolume, buyprice = self.getPriceVolume("buy", regionID, systemName, typeID)
        except PriceError as e:
            return str(e)

        reply = "<b>{}</b> in <b>{}</b>:<br />".format(typeName, systemName)
        reply += "Sells: <b>{:,.2f}</b> ISK -- {:,} units<br />".format(sellprice, sellvolume)
        reply += "Buys: <b>{:,.2f}</b> ISK -- {:,} units<br />".format(buyprice, buyvolume)
        try:
            reply += "Spread: {:,.2%}".format((sellprice - buyprice) / sellprice)
        except ZeroDivisionError:
            # By request from Jack (See https://www.destroyallsoftware.com/talks/wat)
            reply += "Spread: NaNNaNNaNNaNNaNBatman!"

        if items:
            reply += self.disambiguate(args[0], zip(*items)[1], "items")
        if len(args) > 1 and systems:
            reply += self.disambiguate(args[1], zip(*systems)[1], "systems")

        return reply


class APIError(StandardError):
    pass


class EveUtils(object):
    cache_version = 3

    def getTypeName(self, typeID):
        """Resolve a typeID to its name."""
        conn = sqlite3.connect(STATICDATA)
        items = conn.execute(
            """SELECT typeID, typeName
               FROM invTypes
               WHERE typeID = :id;""",
            {'id': typeID}
        ).fetchall()
        conn.close()

        if not items:
            return "{Failed to load}"
        return items[0][1]

    def getSolarSystemData(self, solarSystemID):
        """Resolve a solarSystemID to its data."""
        conn = sqlite3.connect(STATICDATA)
        systems = conn.execute(
            """SELECT solarSystemID, solarSystemName,
                      mapSolarSystems.constellationID, constellationName,
                      mapSolarSystems.regionID, regionName
               FROM mapSolarSystems
               INNER JOIN mapConstellations
                 ON mapConstellations.constellationID = mapSolarSystems.constellationID
               INNER JOIN mapRegions
                 ON mapRegions.regionID = mapSolarSystems.regionID
               WHERE solarSystemID = :id;""",
            {'id': solarSystemID}
        ).fetchall()
        conn.close()

        if not systems:
            return {'solarSystemID': 0, 'solarSystemName': "{Failed to load}",
                    'constellationID': 0, 'constellationName': "{Failed to load}",
                    'regionID': 0, 'regionName': "{Failed to load}"}
        return {'solarSystemID': systems[0][0], 'solarSystemName': systems[0][1],
                'constellationID': systems[0][2], 'constellationName': systems[0][3],
                'regionID': systems[0][4], 'regionName': systems[0][5]}

    def getEVEXMLEndpoint(self, url, timeout, data=dict()):
        """Parse XML document associated with EVE XML-API url."""
        cached = self.getCache(url, params=data)
        if not cached:
            try:
                r = requests.post(url, data=data, headers={'User-Agent': "XVMX JabberBot"},
                                  timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise APIError("Error while connecting to XML-API: {}".format(e))
            if r.status_code != 200:
                raise APIError("XML-API returned error code {}".format(r.status_code))

            xml = ET.fromstring(r.content)
            self.setCache(
                url, doc=r.content,
                expiry=int(timegm(time.strptime(xml[2].text, "%Y-%m-%d %H:%M:%S"))),
                params=data
            )
        else:
            xml = ET.fromstring(cached)

        return xml

    def getTickers(self, corporationID, allianceID):
        """Resolve corpID/allianceID to their respective ticker(s)."""
        # Corp ticker
        corpTicker = None
        if corporationID:
            corpTicker = "{Failed to load}"
            try:
                xml = self.getEVEXMLEndpoint(
                    "https://api.eveonline.com/corp/CorporationSheet.xml.aspx", 3,
                    {'corporationID': corporationID}
                )

                corpTicker = str(xml[1].find("ticker").text)
                allianceID = allianceID or int(xml[1].find("allianceID").text) or None
            except:
                pass

        # Alliance ticker
        allianceTicker = None
        if allianceID:
            allianceTicker = "{Failed to load}"
            try:
                url = "https://api.eveonline.com/eve/AllianceList.xml.aspx"
                cached = self.getCache(url)
                if not cached:
                    r = requests.get(url, headers={'User-Agent': "XVMX JabberBot"}, timeout=5)
                    if r.status_code != 200:
                        raise APIError("XML-API returned error code {}".format(r.status_code))

                    xml = ET.fromstring(r.content)
                    self.AllianceList = xml
                    self.setCache(
                        url, doc=r.content,
                        expiry=int(timegm(time.strptime(xml[2].text, "%Y-%m-%d %H:%M:%S")))
                    )
                elif not hasattr(self, 'AllianceList'):
                    self.AllianceList = ET.fromstring(cached)

                node = self.AllianceList[1][0].find("*[@allianceID='{}']".format(allianceID))
                allianceTicker = node.attrib['shortName']
            except:
                pass

        return (corpTicker, allianceTicker)

    def formatTickers(self, corporationTicker, allianceTicker):
        "Format ticker(s) like the EVE client does."
        ticker = ""
        if corporationTicker:
            ticker += "[{}] ".format(corporationTicker)
        if allianceTicker:
            # Wrapped in <span></span> to force XHTML parsing
            ticker += "<span>&lt;{}&gt;</span> ".format(allianceTicker)
        return ticker[:-1]

    @botcmd
    def character(self, mess, args):
        """<character name>[, ...] - Displays employment information of character(s)"""
        if not args:
            return "Please provide character name(s), separated by commas"

        args = [item.strip() for item in args.split(',')]
        if len(args) > 10:
            return "Please limit your search to 10 characters at most"

        try:
            xml = self.getEVEXMLEndpoint("https://api.eveonline.com/eve/CharacterID.xml.aspx", 3,
                                         {'names': ','.join(args)})
        except APIError as e:
            return str(e)

        charIDs = [int(character.attrib['characterID']) for character in xml[1][0]
                   if int(character.attrib['characterID'])]

        if not charIDs:
            return "None of these character(s) exist"

        try:
            xml = self.getEVEXMLEndpoint(
                "https://api.eveonline.com/eve/CharacterAffiliation.xml.aspx", 5,
                {'ids': ','.join(map(str, charIDs))}
            )
        except APIError as e:
            return str(e)

        # Basic multi-character information
        charDescriptions = []
        for row in xml[1][0]:
            charName = row.attrib['characterName']
            corpName = row.attrib['corporationName']
            allianceName = row.attrib['allianceName']
            factionName = row.attrib['factionName']
            corpTicker, allianceTicker = self.getTickers(int(row.attrib['corporationID']), None)

            charDescription = "<b>{}</b> is part of corporation <b>{} {}</b>".format(
                charName, corpName, self.formatTickers(corpTicker, None)
            )
            if allianceName:
                charDescription += " in <b>{} {}</b>".format(
                    allianceName, self.formatTickers(None, allianceTicker)
                )
            if factionName:
                charDescription += " which is part of <b>{}</b>".format(factionName)

            charDescriptions.append(charDescription)

        reply = "<br />".join(charDescriptions)

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
            xml = self.getEVEXMLEndpoint(
                "https://api.eveonline.com/eve/CharacterName.xml.aspx",
                3, {'ids': ','.join(map(str, corpIDs))}
            )
        except APIError as e:
            return "{}<br/>Error while loading corp history: {}".format(reply, e)

        corps = {}
        for row in xml[1][0]:
            corpID = row.attrib['characterID']
            corpTicker, allianceTicker = self.getTickers(corpID, None)
            corps[corpID] = {'corpName': row.attrib['name'], 'corpTicker': corpTicker}

        for corpRecord in res['history'][-10:]:
            corpData = corps[corpRecord['corporation_id']]
            reply += "<br />From {} til {} in <b>{} {}</b>".format(
                corpRecord['start_date'],
                corpRecord['end_date'] or "now",
                corpData['corpName'],
                self.formatTickers(corpData['corpTicker'], None)
            )

        if len(res['history']) > 10:
            reply += "<br/>The full history is available under http://evewho.com/pilot/{}/".format(
                res['info']['name'].replace(' ', '+')
            )

        return reply

    @botcmd
    def evetime(self, mess, args):
        """[+offset] - Displays the current evetime, server status and evetime + offset if given"""
        timefmt = "%Y-%m-%d %H:%M:%S"
        evetime = datetime.utcnow()
        reply = "The current EVE time is {}".format(evetime.strftime(timefmt))

        try:
            offset_time = evetime + timedelta(hours=int(args))
            reply += " and {} hour(s) is {}".format(args.strip(), offset_time.strftime(timefmt))
        except ValueError:
            pass

        try:
            xml = self.getEVEXMLEndpoint("https://api.eveonline.com/server/ServerStatus.xml.aspx",
                                         3)
            if xml[1][0].text == "True":
                reply += "\nThe server is online and {} players are playing".format(xml[1][1].text)
            else:
                reply += "\nThe server is offline"
        except:
            pass

        return reply

    @botcmd
    def zbot(self, mess, args):
        """<zKB link> [compact] - Displays statistics of a killmail (as a oneliner with compact)"""
        args = args.strip().split(" ", 1)

        regex = self.zBotRegex.match(args[0])
        if regex is None:
            return "Please provide a link to a zKB Killmail"

        killID = regex.group(1)
        compact = len(args) == 2

        url = "https://zkillboard.com/api/killID/{}/no-items/".format(killID)
        cached = self.getCache(url)
        if not cached:
            try:
                r = requests.get(url, headers={'User-Agent': "XVMX JabberBot"}, timeout=5)
            except requests.exceptions.RequestException as e:
                return "Error while connecting to zKB-API: {}".format(e)
            if r.status_code != 200:
                return "zKB-API returned error code {}".format(r.status_code)

            killdata = r.json()
            self.setCache(url, doc=r.text, expiry=int(time.time() + 24 * 60 * 60))
        else:
            killdata = json.loads(cached)

        if not killdata:
            return "Failed to find a killmail for {}".format(regex.group(0))

        victim = killdata[0]['victim']
        solarSystemData = self.getSolarSystemData(killdata[0]['solarSystemID'])
        attackers = killdata[0]['attackers']
        corpTicker, allianceTicker = self.getTickers(victim['corporationID'], victim['allianceID'])

        reply = "{} {} | {} | {:.2f} ISK | {} ({}) | {} participants | {}".format(
            victim['characterName'] or victim['corporationName'],
            self.formatTickers(corpTicker, allianceTicker),
            self.getTypeName(victim['shipTypeID']),
            ISK(killdata[0]['zkb']['totalValue']),
            solarSystemData['solarSystemName'],
            solarSystemData['regionName'],
            len(attackers),
            killdata[0]['killTime']
        )

        if compact:
            return reply

        if victim['characterName']:
            reply += "<br /><b>{}</b> is part of corporation <b>{} {}</b>".format(
                victim['characterName'], victim['corporationName'],
                self.formatTickers(corpTicker, None)
            )
        else:
            reply += "<br />The structure is owned by corporation <b>{} {}</b>".format(
                victim['corporationName'], self.formatTickers(corpTicker, None)
            )
        if victim['allianceName']:
            reply += " in <b>{} {}</b>".format(victim['allianceName'],
                                               self.formatTickers(None, allianceTicker))
        if victim['factionName']:
            reply += " which is part of <b>{}</b>".format(victim['factionName'])

        reply += " and took <b>{:,} damage</b> for <b>{:,} point(s)</b>".format(
            victim['damageTaken'], killdata[0]['zkb']['points']
        )

        attackerDetails = [{'characterName': char['characterName'],
                            'corporationID': char['corporationID'],
                            'corporationName': char['corporationName'],
                            'damageDone': char['damageDone'],
                            'shipTypeName': self.getTypeName(char['shipTypeID']),
                            'finalBlow': bool(char['finalBlow'])} for char in attackers]
        # Sort after inflicted damage
        attackerDetails.sort(key=lambda x: x['damageDone'], reverse=True)

        # Add attackerDetails
        detailedInfo = "<b>{}</b> {} (<b>{}</b>) inflicted <b>{:,} damage</b> "
        detailedInfo += "(<i>{:,.2%} of total damage</i>)"
        for char in attackerDetails[:5]:
            corpTicker, allianceTicker = self.getTickers(char['corporationID'], None)

            reply += "<br />"
            reply += detailedInfo.format(char['characterName'] or char['corporationName'],
                                         self.formatTickers(corpTicker, allianceTicker),
                                         char['shipTypeName'], char['damageDone'],
                                         char['damageDone'] / float(victim['damageTaken']))
            reply += " and scored the <b>final blow</b>" if char['finalBlow'] else ""

        # Add final blow if not already included
        if "final blow" not in reply:
            char = [char for char in attackerDetails if char['finalBlow']][0]
            corpTicker, allianceTicker = self.getTickers(char['corporationID'], None)

            reply += "<br />"
            reply += detailedInfo.format(char['characterName'] or char['corporationName'],
                                         self.formatTickers(corpTicker, allianceTicker),
                                         char['shipTypeName'], char['damageDone'],
                                         char['damageDone'] / float(victim['damageTaken']))
            reply += " and scored the <b>final blow</b>"

        return reply

    def kmFeed(self):
        """Send a message to the first chatroom with the latest losses."""
        url = "https://zkillboard.com/api/corporationID/2052404106/losses/"
        url += "afterKillID/{}/no-items/no-attackers/".format(self.kmFeedID)

        try:
            r = requests.get(url, headers={'User-Agent': "XVMX JabberBot"}, timeout=5)
        except requests.exceptions.RequestException:
            return
        if r.status_code != 200:
            return

        minimumValue = 5000000
        losses = filter(lambda x: x['zkb']['totalValue'] >= minimumValue, r.json())
        if not losses:
            return

        self.kmFeedID = losses[0]['killID']

        reply = "{} new loss(es):".format(len(losses))
        for loss in reversed(losses):
            victim = loss['victim']
            solarSystemData = self.getSolarSystemData(loss['solarSystemID'])

            reply += "<br/>{} {} | {} | {:.2f} ISK | {} ({}) | {} | {}".format(
                victim['characterName'] or victim['corporationName'],
                self.formatTickers("XVMX", "CONDI"),
                self.getTypeName(victim['shipTypeID']),
                ISK(loss['zkb']['totalValue']),
                solarSystemData['solarSystemName'],
                solarSystemData['regionName'],
                loss['killTime'],
                "https://zkillboard.com/kill/{}/".format(loss['killID'])
            )

        self.send(vmc['jabber']['chatroom1'], reply, message_type="groupchat")

    def newsFeed(self):
        """Send a message to the first chatroom with the latest EVE news and devblogs."""
        def getCCPFeed(feedType):
            """Find all new Atom entries available at feedType.

            feedType must be either "news" or "devblog".
            """
            if feedType == "news":
                url = "http://newsfeed.eveonline.com/en-US/44/articles/page/1/20"
            elif feedType == "devblog":
                url = "http://newsfeed.eveonline.com/en-US/2/articles/page/1/20"
            else:
                raise ValueError('feedType must be either "news" or "devblog"')

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

            if self.newsFeedIDs[feedType] is None:
                self.newsFeedIDs[feedType] = entries[0]['id']
                return []
            else:
                idx = next(idx for (idx, entry) in enumerate(entries)
                           if entry['id'] == self.newsFeedIDs[feedType])
                self.newsFeedIDs[feedType] = entries[0]['id']
                return entries[:idx]

        newsEntries = None
        devblogEntries = None
        try:
            newsEntries = getCCPFeed("news")
        except:
            pass
        try:
            devblogEntries = getCCPFeed("devblog")
        except:
            pass

        if newsEntries:
            reply = "{} new EVE news:".format(len(newsEntries))
            for entry in newsEntries:
                reply += "<br /><b>{}</b>: {}".format(entry['title'], entry['url'])
            self.send(vmc['jabber']['chatroom1'], reply, message_type="groupchat")

        if devblogEntries:
            reply = "{} new devblog(s):".format(len(devblogEntries))
            for entry in devblogEntries:
                reply += "<br /><b>{}</b>: {}".format(entry['title'], entry['url'])
            self.send(vmc['jabber']['chatroom1'], reply, message_type="groupchat")

    @botcmd
    def rcbl(self, mess, args):
        """<name>[, ...] - Displays if name has an entry in the blacklist"""
        # Remove verify=False as soon as python 2.7.7 hits (exp. May 31, 2014).
        # Needed due to self-signed cert with multiple domains + requests/urllib3
        # Ref.:
        #     https://github.com/kennethreitz/requests/issues/1977
        #     http://legacy.python.org/dev/peps/pep-0466/
        #     http://legacy.python.org/dev/peps/pep-0373/
        blrequest = "{}{}/".format(vmc['blacklist']['url'], vmc['blacklist']['key'])
        results = []
        for pilot in [item.strip() for item in args.split(',')]:
            try:
                r = requests.get(blrequest + pilot,
                                 headers={'User-Agent': "XVMX JabberBot"}, timeout=3, verify=False)
                results.append("{} is {}".format(pilot, r.json()[0]['output']))
            except:
                pass

        return "<br />".join(results)

    def getCache(self, path, params=dict()):
        conn = sqlite3.connect(APICACHE)
        conn.text_factory = str

        try:
            if not params:
                res = conn.execute(
                    """SELECT response
                       FROM cache
                       WHERE path = :path
                         AND expiry > :expiry;""",
                    {'path': path, 'expiry': time.time()}
                ).fetchall()
            else:
                res = conn.execute(
                    """SELECT response
                       FROM cache
                       WHERE path = :path
                         AND params = :params
                         AND expiry > :expiry;""",
                    {'path': path, 'params': json.dumps(params), 'expiry': int(time.time())}
                ).fetchall()
        except:
            conn.close()
            return None

        conn.close()
        return res[0][0] if len(res) == 1 else None

    def setCache(self, path, doc, expiry, params=dict()):
        conn = sqlite3.connect(APICACHE)
        conn.text_factory = str

        conn.execute(
            """CREATE TABLE IF NOT EXISTS metadata (
                 type TEXT NOT NULL UNIQUE,
                 value INTEGER NOT NULL
               );"""
        )

        res = conn.execute(
            """SELECT value
               FROM metadata
               WHERE type = "version";"""
        ).fetchall()
        if res and res[0][0] < self.cache_version:
            conn.execute("DROP TABLE cache;")
        conn.commit()

        conn.execute(
            """INSERT OR REPLACE INTO metadata
               VALUES ("version", :version);""",
            {'version': self.cache_version}
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS cache (
                 path TEXT NOT NULL,
                 params TEXT,
                 response TEXT NOT NULL,
                 expiry INTEGER NOT NULL,
                 CONSTRAINT Query UNIQUE (path, params)
               );"""
        )
        conn.execute(
            """DELETE FROM cache
               WHERE expiry <= :expiry;""",
            {'expiry': int(time.time())}
        )
        conn.commit()

        if not params:
            conn.execute(
                """INSERT INTO cache
                   VALUES (:path, "", :response, :expiry);""",
                {'path': path, 'response': doc, 'expiry': expiry}
            )
        else:
            conn.execute(
                """INSERT INTO cache
                   VALUES (:path, :params, :response, :expiry);""",
                {'path': path, 'params': json.dumps(params), 'response': doc, 'expiry': expiry}
            )

        conn.commit()
        conn.close()
        return True
