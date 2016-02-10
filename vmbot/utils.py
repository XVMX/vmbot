from jabberbot import botcmd

import time
from datetime import datetime, timedelta
import calendar
import re
import json
import xml.etree.ElementTree as ET
import sqlite3

import requests

import vmbot_config as vmc


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

        conn = sqlite3.connect("data/staticdata.sqlite")
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
        conn = sqlite3.connect("data/staticdata.sqlite")
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
        conn = sqlite3.connect("data/staticdata.sqlite")
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

            xml = ET.fromstring(r.text)
            self.setCache(
                url, doc=r.text,
                expiry=int(calendar.timegm(time.strptime(xml[2].text, "%Y-%m-%d %H:%M:%S"))),
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

                    xml = ET.fromstring(r.text)
                    self.AllianceList = xml
                    self.setCache(
                        url, doc=r.text,
                        expiry=int(calendar.timegm(time.strptime(xml[2].text, "%Y-%m-%d %H:%M:%S")))
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
        '''<character name> - Displays Employment information of a single character

<character name,character name,...> Displays Employment information of multiple characters'''
        try:
            args = [item.strip() for item in args.strip().split(',')]
            if args[0] == '':
                return 'Please provide character name(s), separated by commas'
            if len(args) > 10:
                return 'Please limit your search to 10 characters at once'
            reply = ''
            cached = self.getCache('https://api.eveonline.com/eve/CharacterID.xml.aspx',
                                   params={'names': ','.join(map(str, args))})
            if not cached:
                r = requests.post('https://api.eveonline.com/eve/CharacterID.xml.aspx',
                                  data={'names': ','.join(map(str, args))},
                                  headers={'User-Agent': 'VM JabberBot'},
                                  timeout=3)
                if r.status_code != 200 or r.encoding != 'utf-8':
                    return ('The CharacterID-API returned error code <b>{}</b>'
                            ' or the XML encoding is broken.').format(r.status_code)
                xml = ET.fromstring(r.text)
                self.setCache('https://api.eveonline.com/eve/CharacterID.xml.aspx',
                              doc=str(r.text),
                              expiry=int(calendar.timegm(
                                  time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                              params={'names': ','.join(map(str, args))})
            else:
                xml = ET.fromstring(cached)
            args = []
            for character in xml[1][0]:
                if int(character.attrib['characterID']) != 0:
                    args.append(character.attrib['characterID'])
                else:
                    reply += 'Character <b>{}</b> does not exist<br />'.format(
                        character.attrib['name'])
            if len(args) == 0:
                return 'None of these character(s) exist'
            cached = self.getCache('https://api.eveonline.com/eve/CharacterAffiliation.xml.aspx',
                                   params={'ids': ','.join(map(str, args))})
            if not cached:
                r = requests.post('https://api.eveonline.com/eve/CharacterAffiliation.xml.aspx',
                                  data={'ids': ','.join(map(str, args))},
                                  headers={'User-Agent': 'VM JabberBot'},
                                  timeout=4)
                if r.status_code != 200 or r.encoding != 'utf-8':
                    return ('The CharacterAffiliation-API returned error code <b>{}</b>'
                            ' or the XML encoding is broken.').format(r.status_code)
                xml = ET.fromstring(r.text)
                self.setCache('https://api.eveonline.com/eve/CharacterAffiliation.xml.aspx',
                              doc=str(r.text),
                              expiry=int(calendar.timegm(
                                  time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                              params={'ids': ','.join(map(str, args))})
            else:
                xml = ET.fromstring(cached)
            for row in xml[1][0]:
                character = row.attrib
                reply += str(character['characterName'])
                reply += ' is in corporation <b>' + str(character['corporationName']) + '</b>'
                reply += ((' in alliance <b>{}</b>'.format(character['allianceName']))
                          if str(character['allianceName']) != '' else '')
                reply += ((' in faction <b>{}</b>'.format(character['factionName']))
                          if str(character['factionName']) != '' else '')
                reply += '<br />'
            if len(args) == 1:
                r = requests.get('http://evewho.com/api.php',
                                 params={'type': 'character', 'id': args[0]},
                                 headers={'User-Agent': 'VM JabberBot'},
                                 timeout=5)
                if r.status_code != 200:
                    return 'The EVEWho-API returned error code <b>{}</b>.'.format(r.status_code)
                evewhoapi = r.json()
                if evewhoapi['info'] is None:
                    reply += 'Eve Who got no data for this character<br />'
                else:
                    reply += 'Security status: <b>{}</b><br />'.format(
                        evewhoapi['info']['sec_status'])
                    corporations = []
                    for corp in evewhoapi['history'][-10:]:
                        corporations.append(corp['corporation_id'])
                    corporations = list(set(corporations))
                    cached = self.getCache('https://api.eveonline.com/eve/charactername.xml.aspx',
                                           params={'ids': ','.join(map(str, corporations))})
                    if not cached:
                        r = requests.post('https://api.eveonline.com/eve/charactername.xml.aspx',
                                          data={'ids': ','.join(map(str, corporations))},
                                          timeout=3)
                        if r.status_code != 200 or r.encoding != 'utf-8':
                            return ('The CharacterAffiliation-API returned error code <b>{}</b>'
                                    ' or the XML encoding is broken.').format(r.status_code)
                        xml = ET.fromstring(r.text)
                        self.setCache('https://api.eveonline.com/eve/charactername.xml.aspx',
                                      doc=str(r.text),
                                      expiry=int(calendar.timegm(
                                          time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                                      params={'ids': ','.join(map(str, corporations))})
                    else:
                        xml = ET.fromstring(cached)
                    corporations = {}
                    for corp in xml[1][0]:
                        corporations[corp.attrib['characterID']] = corp.attrib['name']
                    for corp in evewhoapi['history'][-10:]:
                        reply += 'From ' + str(corp['start_date'])
                        reply += ' til ' + (str(corp['end_date'])
                                            if str(corp['end_date']) != 'None' else 'now')
                        reply += ' in <b>' + str(corporations[corp['corporation_id']]) + '</b>'
                        reply += '<br />'
                    if len(evewhoapi['history']) > 10:
                        reply += ('The full history is available under '
                                  'http://evewho.com/pilot/{}/<br />').format(
                                      str(evewhoapi['info']['name']).replace(' ', '+'))
            reply = reply[:-6]
        except requests.exceptions.RequestException as e:
            return 'There is a problem with the API server. Can\'t connect to the server.'
        return reply

    @botcmd
    def evetime(self, mess, args):
        '''Displays the current evetime and server status

<+offset> - Displays the current evetime, server status and the resulting evetime of the offset'''
        timefmt = '%Y-%m-%d %H:%M:%S'
        evetime = datetime.utcnow()
        reply = 'The current EVE time is ' + evetime.strftime(timefmt)
        try:
            offset_time = timedelta(hours=int(args)) + evetime
            reply += ' and {} hour(s) is {}'.format(args.strip(), offset_time.strftime(timefmt))
        except ValueError:
            pass
        try:
            cached = self.getCache('https://api.eveonline.com/server/serverstatus.xml.aspx')
            if not cached:
                r = requests.get('https://api.eveonline.com/server/serverstatus.xml.aspx',
                                 headers={'User-Agent': 'VM JabberBot'},
                                 timeout=3)
                if r.status_code != 200 or r.encoding != 'utf-8':
                    return ('The ServerStatus-API returned error code <b>{}</b>'
                            ' or the XML encoding is broken.').format(r.status_code)
                xml = ET.fromstring(r.text)
                self.setCache('https://api.eveonline.com/server/serverstatus.xml.aspx',
                              doc=str(r.text),
                              expiry=int(calendar.timegm(
                                  time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))))
            else:
                xml = ET.fromstring(cached)
            if xml[1][0].text == 'True':
                reply += '\nThe server is online and {} players are playing'.format(xml[1][1].text)
            else:
                reply += '\nThe server is offline'
        except requests.exceptions.RequestException as e:
            reply += '\nThere is a problem with the API server. Can\'t access ServerStatus-API.'
        return reply

    @botcmd
    def zbot(self, mess, args):
        '''<zKB link> - Displays statistics of a killmail

<zKB link> compact - Displays statistics of a killmail in one line'''

        args = args.strip().split(" ", 1)
        regex = re.match('https?:\/\/zkillboard\.com\/kill\/(\d+)\/?', args[0])
        if regex is None:
            return 'Please provide a link to a zKB Killmail'
        killID = regex.group(1)
        compact = len(args) == 2

        cached = self.getCache('https://zkillboard.com/api/killID/{}/no-items/'.format(killID))
        if not cached:
            r = requests.get('https://zkillboard.com/api/killID/{}/no-items/'.format(killID),
                             headers={'Accept-Encoding': 'gzip',
                                      'User-Agent': 'VM JabberBot'},
                             timeout=5)
            if r.status_code != 200 or r.encoding != 'utf-8':
                return ('The zKB-API returned error code <b>{}</b>'
                        ' or the encoding is broken.').format(r.status_code)
            killdata = r.json()
            self.setCache('https://zkillboard.com/api/killID/{}/no-items/'.format(killID),
                          doc=str(r.text),
                          expiry=int(time.time() + 24 * 60 * 60))
        else:
            killdata = json.loads(cached)

        if not killdata:
            return "Can't find a killmail for {}".format(regex.group(0))

        victim = killdata[0]['victim']
        solarSystemData = self.getSolarSystemData(int(killdata[0]['solarSystemID']))
        killTime = str(killdata[0]['killTime'])
        attackers = killdata[0]['attackers']
        totalValue = ISK(killdata[0]['zkb']['totalValue'])
        points = int(killdata[0]['zkb']['points'])

        corpTicker, allianceTicker = self.getTickers(victim['corporationID'], victim['allianceID'])
        ticker = ""
        if victim['characterName']:
            ticker += "["
            ticker += str(corpTicker)
            ticker += " | {}".format(allianceTicker) if allianceTicker else ""
            ticker += "] "
        elif allianceTicker:
            ticker += "[{}] ".format(allianceTicker)

        reply = "{} {}| {} | {:.2f} ISK | {} ({}) | {} participants | {}".format(
            victim['characterName'] if victim['characterName'] else victim['corporationName'],
            ticker,
            self.getTypeName(victim['shipTypeID']),
            totalValue,
            solarSystemData['solarSystemName'],
            solarSystemData['regionName'],
            len(attackers),
            killTime
        )

        if compact:
            return reply

        reply += '<br />'
        if victim['characterName']:
            reply += '{} is in corporation {}'.format(
                victim['characterName'], victim['corporationName'])
            reply += (' in alliance {}'.format(victim['allianceName'])
                      if victim['allianceName'] else '')
            reply += (' in faction {}'.format(victim['factionName'])
                      if victim['factionName'] else '')
        else:
            reply += 'The POS is owned by corporation {}'.format(victim['corporationName'])
            reply += (' in alliance {}'.format(victim['allianceName'])
                      if victim['allianceName'] else '')
            reply += (' in faction {}'.format(victim['factionName'])
                      if victim['factionName'] else '')
        reply += ' and took <b>{:,}</b> damage'.format(victim['damageTaken'])
        reply += ' for <b>{:,} point(s)</b>'.format(points)
        reply += '<br />'

        attackerDetails = list()
        for char in attackers:
            attackerDetails.append({'characterName': str(char['characterName']),
                                    'corporationName': str(char['corporationName']),
                                    'damageDone': int(char['damageDone']),
                                    'shipTypeID': int(char['shipTypeID']),
                                    'finalBlow': char['finalBlow'] == 1})
        # Sort after inflicted damage
        attackerDetails.sort(key=lambda x: x['damageDone'], reverse=True)

        # Add ship type names to attackerDetails
        for char in attackerDetails:
            char['shipTypeName'] = str(self.getTypeName(char['shipTypeID']))

        # Print attackerDetails
        for char in attackerDetails[:5]:
            reply += ('<b>{}\'s {}</b> did <b>{:,} damage</b>'
                      ' (<i>{:,.2%} of total damage</i>)').format(
                          char['characterName'] or char['corporationName'],
                          char['shipTypeName'],
                          char['damageDone'],
                          char['damageDone'] / float(victim['damageTaken']))
            reply += ' and scored the <b>final blow</b>' if char['finalBlow'] else ''
            reply += '<br />'

        # Print final blow if not already included
        if "final blow" not in reply:
            char = [char for char in attackerDetails if char['finalBlow']][0]
            reply += ('<b>{}\'s {}</b> did <b>{:,} damage</b>'
                      ' (<i>{:,.2%} of total damage</i>)').format(
                          char['characterName'] or char['corporationName'],
                          char['shipTypeName'],
                          char['damageDone'],
                          char['damageDone'] / float(victim['damageTaken']))
            reply += ' and scored the <b>final blow</b>'
            reply += '<br />'

        return reply[:-6]

    def kmFeed(self):
        '''Sends a message to the first chatroom with the latest losses'''

        r = requests.get(('https://zkillboard.com/api/corporationID/2052404106/losses/'
                          'afterKillID/{}/no-items/no-attackers/').format(self.kmFeedID),
                         headers={'Accept-Encoding': 'gzip',
                                  'User-Agent': 'VM JabberBot'},
                         timeout=5)
        if r.status_code != 200 or r.encoding != 'utf-8':
            return

        losses = r.json()
        if losses:
            self.kmFeedID = int(losses[0]['killID'])
            reply = "{} new loss(es):<br />".format(len(losses))
            for loss in losses:
                killID = int(loss['killID'])
                victim = loss['victim']
                solarSystemData = self.getSolarSystemData(int(loss['solarSystemID']))
                killTime = str(loss['killTime'])
                totalValue = ISK(loss['zkb']['totalValue'])
                ticker = "XVMX | CONDI" if victim['characterName'] else "CONDI"

                reply += "{} [{}] | {} | {:.2f} ISK | {} ({}) | {} | {}".format(
                    victim['characterName'] if victim['characterName']
                    else victim['corporationName'],
                    ticker,
                    self.getTypeName(victim['shipTypeID']),
                    totalValue,
                    solarSystemData['solarSystemName'],
                    solarSystemData['regionName'],
                    killTime,
                    "https://zkillboard.com/kill/{}/".format(killID)
                )
                reply += "<br />"
            reply = reply[:-6]
            self.send(vmc.chatroom1, reply, in_reply_to=None, message_type='groupchat')

        return

    @botcmd
    def rcbl(self, mess, args):
        '''<name>[, ...] - Asks the RC API if <pilot name> has an entry in the blacklist.'''
        # Remove verify=False as soon as python 2.7.7 hits (exp. May 31, 2014).
        # Needed due to self-signed cert with multiple domains + requests/urllib3
        # Ref.:
        #     https://github.com/kennethreitz/requests/issues/1977
        #     http://legacy.python.org/dev/peps/pep-0466/
        #     http://legacy.python.org/dev/peps/pep-0373/
        result = []
        for pilot in [a.strip() for a in args.split(',')]:
            response = requests.get(''.join([vmc.blurl, vmc.blkey, '/', pilot]), verify=False)
            result.append('{} is {}'.format(pilot, response.json()[0]['output']))

        if len(result) > 1:
            result.insert(0, '')
        return '<br />'.join(result)

    def getCache(self, path, params=dict()):
        conn = sqlite3.connect("data/api.cache")

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
        conn = sqlite3.connect("data/api.cache")

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
