from jabberbot import botcmd

from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import time
import re
import requests
import json
import calendar
import base64
import vmbot_config as vmc
import sqlite3

from sympy.parsing.sympy_parser import parse_expr


class CREST(object):
    class CRESTError(StandardError):
        pass

    def getAccessToken(self):
        try:
            self._access_token
            self._token_expiry
        except AttributeError:
            self._access_token = ''
            self._token_expiry = 0

        if self._token_expiry >= time.time():
            return self._access_token

        # FIXME: check on instantiation
        assert(vmc.refresh_token)
        assert(vmc.client_secret)

        data = {'grant_type': 'refresh_token',
                'refresh_token': vmc.refresh_token}
        headers = {'Authorization': 'Basic ' + base64.b64encode('{}:{}'.format(vmc.client_id, vmc.client_secret)),
                   'User-Agent': 'VM JabberBot'}
        r = requests.post('https://login.eveonline.com/oauth/token',
                          data=data, headers=headers)

        res = r.json()
        try:
            self._access_token = res['access_token']
            self._token_expiry = time.time()+res['expires_in']
        except KeyError:
            raise self.CRESTError('Error: {}: {}'.format(res['error'], res['error_description']))
        return self._access_token


class Price(object):
    class PriceError(StandardError):
        pass

    def getPriceVolume(self, orderType, region, system, item):
        url = 'https://crest-tq.eveonline.com/market/{}/orders/{}/'.format(region, orderType)
        url += '?type=https://crest-tq.eveonline.com/types/{}/'.format(item)
        header = {'Authorization': 'Bearer {}'.format(self.getAccessToken()),
                  'User-Agent': 'VM JabberBot'}
        try:
            r = requests.get(url, headers=header, timeout=5)
        except requests.exceptions.RequestException as e:
            raise self.PriceError("Error connecting to CREST servers: {!s}".format(e))
        if r.status_code != 200:
            raise self.PriceError('The CREST-API returned error <b>{!s}</b>'.format(r.status_code))
        res = r.json()

        volume = sum([order['volume'] for order in res['items'] if order['location']['name'].startswith(system)])
        direction = (min if orderType == 'sell' else max)
        try:
            price = direction([order['price'] for order in res['items'] if order['location']['name'].startswith(system)])
        except ValueError:
            price = 0

        return (volume, price)

    def disambiguate(self, given, like, category):
        if like:
            reply = '<br />Other {} like "{}": {}'.format(category, given, ', '.join(like[:3]))
            if len(like) > 3:
                reply += ', and {} others'.format(len(like)-3)
            return reply
        else:
            return ''

    @botcmd
    def price(self, mess, args):
        '''<item>@[system] - Displays price of item in system, defaulting to Jita'''
        args = [item.strip() for item in args.strip().split('@')]
        if len(args) < 1 or len(args) > 2 or args[0] == '':
            return 'Please specify one item name and optional one system name: <item>@[system]'

        item = args[0]
        try:
            system = args[1]
        except IndexError:
            system = 'Jita'

        if item.lower() in ('plex', 'pilot license', 'pilot license extension', "pilot's license extension"):
            item = "30 Day Pilot's License Extension (PLEX)"

        conn = sqlite3.connect('staticdata.sqlite')
        cur = conn.cursor()
        cur.execute(
            '''SELECT regionID, solarSystemName
               FROM mapSolarSystems
               WHERE solarSystemName LIKE :name;''',
            {'name': '%'+system+'%'})
        systems = cur.fetchall()
        if not systems:
            return "Can't find a matching system!"

        cur.execute(
            '''SELECT typeID, typeName
               FROM invTypes
               WHERE typeName LIKE :name
                AND marketGroupID IS NOT NULL
                AND marketGroupID < 100000;''',
            {'name': '%'+item+'%'})
        items = cur.fetchall()
        if not items:
            return "Can't find a matching item!"
        cur.close()
        conn.close()

        # Sort by length of name so that the most similar item is first
        items.sort(lambda x, y: cmp(len(x[1]), len(y[1])))
        systems.sort(lambda x, y: cmp(len(x[1]), len(y[1])))

        typeID, typeName = items.pop(0)
        regionID, systemName = systems.pop(0)

        try:
            sellvolume, sellprice = self.getPriceVolume('sell', regionID, systemName, typeID)
            buyvolume, buyprice = self.getPriceVolume('buy', regionID, systemName, typeID)
        except (self.CRESTError, self.PriceError) as e:
            return str(e)

        reply = '<b>{}</b> in <b>{}</b>:<br />'.format(typeName, systemName)
        reply += 'Sells: <b>{:,.2f}</b> ISK -- {:,} units<br />'.format(sellprice, sellvolume)
        reply += 'Buys: <b>{:,.2f}</b> ISK -- {:,} units'.format(buyprice, buyvolume)
        try:
            reply += '<br />Spread: {:,.2%}'.format((sellprice-buyprice)/sellprice)
        except ZeroDivisionError:
            # By request from Jack
            reply += '<br />Spread: NaNNaNNaNNaNNaNBatman!'

        if args and items:
            reply += self.disambiguate(args[0], zip(*items)[1], "items")
        if len(args) > 1 and systems:
            reply += self.disambiguate(args[1], zip(*systems)[1], "systems")

        return reply


class EveUtils(object):
    cache_version = 1

    @botcmd
    def character(self, mess, args):
        '''<character name> - Displays Corporation, Alliance, Faction, SecStatus and Employment History of a single character
        <character name,character name,character name,...> Displays Corporation, Alliance and Faction of multiple characters'''
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
                    return 'The CharacterID-API returned error code <b>{!s}</b> or the XML encoding is broken.'.format(r.status_code)
                xml = ET.fromstring(r.text)
                self.setCache('https://api.eveonline.com/eve/CharacterID.xml.aspx',
                              doc=str(r.text),
                              expiry=int(calendar.timegm(time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                              params={'names': ','.join(map(str, args))})
            else:
                xml = ET.fromstring(cached)
            args = []
            for character in xml[1][0]:
                if int(character.attrib['characterID']) != 0:
                    args.append(character.attrib['characterID'])
                else:
                    reply += 'Character <b>{}</b> does not exist<br />'.format(character.attrib['name'])
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
                    return 'The CharacterAffiliation-API returned error code <b>{!s}</b> or the XML encoding is broken.'.format(r.status_code)
                xml = ET.fromstring(r.text)
                self.setCache('https://api.eveonline.com/eve/CharacterAffiliation.xml.aspx',
                              doc=str(r.text),
                              expiry=int(calendar.timegm(time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                              params={'ids': ','.join(map(str, args))})
            else:
                xml = ET.fromstring(cached)
            for row in xml[1][0]:
                character = row.attrib
                reply += str(character['characterName'])
                reply += ' is in corporation <b>' + str(character['corporationName']) + '</b>'
                reply += ((' in alliance <b>{!s}</b>'.format(character['allianceName'])) if str(character['allianceName']) != '' else '')
                reply += ((' in faction <b>{!s}</b>'.format(character['factionName'])) if str(character['factionName']) != '' else '')
                reply += '<br />'
            if len(args) == 1:
                r = requests.get('http://evewho.com/api.php',
                                 params={'type': 'character', 'id': args[0]},
                                 headers={'User-Agent': 'VM JabberBot'},
                                 timeout=5)
                if r.status_code != 200:
                    return 'The EVEWho-API returned error code <b>{!s}</b>.'.format(r.status_code)
                evewhoapi = r.json()
                if evewhoapi['info'] == None:
                    reply += 'Eve Who got no data for this character<br />'
                else:
                    reply += 'Security status: <b>{!s}</b><br />'.format(evewhoapi['info']['sec_status'])
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
                            return 'The CharacterAffiliation-API returned error code <b>{!s}</b> or the XML encoding is broken.'.format(r.status_code)
                        xml = ET.fromstring(r.text)
                        self.setCache('https://api.eveonline.com/eve/charactername.xml.aspx',
                                      doc=str(r.text),
                                      expiry=int(calendar.timegm(time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                                      params={'ids': ','.join(map(str, corporations))})
                    else:
                        xml = ET.fromstring(cached)
                    corporations = {}
                    for corp in xml[1][0]:
                        corporations[corp.attrib['characterID']] = corp.attrib['name']
                    for corp in evewhoapi['history'][-10:]:
                        reply += 'From ' + str(corp['start_date'])
                        reply += ' til ' + (str(corp['end_date']) if str(corp['end_date']) != 'None' else 'now')
                        reply += ' in <b>' + str(corporations[corp['corporation_id']]) + '</b><br />'
                    if len(evewhoapi['history']) > 10:
                        reply += 'The full history is available under http://evewho.com/pilot/{}/<br />'.format(str(evewhoapi['info']['name']).replace(' ', '+'))
            reply = reply[:-6]
        except requests.exceptions.RequestException as e:
            return 'There is a problem with the API server. Can\'t connect to the server.'
        return reply

    @botcmd
    def evetime(self, mess, args):
        '''[+offset] - Displays the current evetime, server status and the resulting evetime of the offset, if provided'''
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
                    return 'The ServerStatus-API returned error code <b>{!s}</b> or the XML encoding is broken.'.format(r.status_code)
                xml = ET.fromstring(r.text)
                self.setCache('https://api.eveonline.com/server/serverstatus.xml.aspx',
                              doc=str(r.text),
                              expiry=int(calendar.timegm(time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))))
            else:
                xml = ET.fromstring(cached)
            if xml[1][0].text == 'True':
                reply += '\nThe server is online and {!s} players are playing'.format(xml[1][1].text)
            else:
                reply += '\nThe server is offline'
        except requests.exceptions.RequestException as e:
            reply += '\nThere is a problem with the API server. Can\'t access ServerStatus-API.'
        return reply

    @botcmd
    def zbot(self, mess, args):
        '''<zKB link> - Displays statistics of a killmail'''
        try:
            # Resolves typeIDs to their names
            def getTypeName(pID):
                try:
                    cached = self.getCache('https://api.eveonline.com/eve/TypeName.xml.aspx',
                                           params={'ids': pID})
                    if not cached:
                        r = requests.post('https://api.eveonline.com/eve/TypeName.xml.aspx',
                                          data={'ids': pID},
                                          headers={'User-Agent': 'VM JabberBot'},
                                          timeout=3)
                        xml = ET.fromstring(r.text)
                        self.setCache('https://api.eveonline.com/eve/TypeName.xml.aspx',
                                      doc=str(r.text),
                                      expiry=int(calendar.timegm(time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                                      params={'ids': pID})
                    else:
                        xml = ET.fromstring(cached)
                    apireply = str(xml[1][0][0].attrib['typeName'])
                except:
                    apireply = str('[API Error]')
                finally:
                    return apireply

            # Resolves IDs to their names; can be used to resolve characterID, agentID, corporationID, allianceID, factionID
            def getName(pID):
                    try:
                        cached = self.getCache('https://api.eveonline.com/eve/charactername.xml.aspx',
                                               params={'ids': pID})
                        if not cached:
                            r = requests.post('https://api.eveonline.com/eve/charactername.xml.aspx',
                                              data={'ids': pID},
                                              headers={'User-Agent': 'VM JabberBot'},
                                              timeout=3)
                            xml = ET.fromstring(r.text)
                            self.setCache('https://api.eveonline.com/eve/charactername.xml.aspx',
                                          doc=str(r.text),
                                          expiry=int(calendar.timegm(time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                                          params={'ids': pID})
                        else:
                            xml = ET.fromstring(cached)
                        apireply = str(xml[1][0][0].attrib['name'])
                    except:
                        apireply = str('[API Error]')
                    finally:
                        return apireply

            args = args.strip()
            regex = re.match('https?:\/\/zkillboard\.com\/kill\/(\d+)\/?', args)
            if regex is None:
                return 'Please provide a link to a zKB Killmail'
            args = regex.group(1)

            cached = self.getCache('https://zkillboard.com/api/killID/{!s}/').format(args)
            if not cached:
                r = requests.get('https://zkillboard.com/api/killID/{!s}/'.format(args),
                                 headers={'Accept-Encoding': 'gzip',
                                          'User-Agent': 'VM JabberBot'},
                                 timeout=6)
                if r.status_code != 200 or r.encoding != 'utf-8':
                    return 'The zKB-API returned error code <b>{!s}</b> or the encoding is broken.'.format(r.status_code)
                killdata = r.json()
                self.setCache('https://zkillboard.com/api/killID/{!s}/'.format(args),
                              doc=str(r.text),
                              expiry=int(time.time()+24*60*60))
            else:
                killdata = json.loads(cached)

            victim = killdata[0]['victim']
            solarSystemID = int(killdata[0]['solarSystemID'])
            killTime = str(killdata[0]['killTime'])
            attackers = killdata[0]['attackers']
            totalValue = float(killdata[0]['zkb']['totalValue'])
            points = int(killdata[0]['zkb']['points'])

            reply = '<b>{}</b>'.format(str(victim['characterName']) if str(victim['characterName']) != '' else str(victim['corporationName']) + '\'s POS')
            reply += ' got killed while flying a/an <b>{!s}</b>'.format(getTypeName(victim['shipTypeID']))
            reply += ' in <b>' + str(getName(solarSystemID)) + '</b>'
            reply += ' at ' + killTime
            reply += '<br />'
            if str(victim['characterName']) != '':
                reply += str(victim['characterName']) + ' is in corporation ' + str(victim['corporationName'])
                reply += (' in alliance ' + str(victim['allianceName']) if str(victim['allianceName']) != '' else '')
                reply += (' in faction ' + str(victim['factionName']) if str(victim['factionName']) != '' else '')
            else:
                reply += 'The POS is owned by corporation ' + str(victim['corporationName'])
                reply += (' in alliance ' + str(victim['allianceName']) if str(victim['allianceName']) != '' else '')
                reply += (' in faction ' + str(victim['factionName']) if str(victim['factionName']) != '' else '')
            reply += ' and took <b>{:,}</b> damage'.format(int(victim['damageTaken']))
            reply += '<br />'
            reply += 'The total value of the ship/POS was <b>{:,.2f} ISK</b> for <b>{:,} point(s)</b><br />'.format(totalValue, points)

            attackerDetails = list()
            for char in attackers:
                attackerDetails.append({'characterName': str(char['characterName']),
                                        'corporationName': str(char['corporationName']),
                                        'damageDone': int(char['damageDone']),
                                        'shipTypeID': int(char['shipTypeID']),
                                        'finalBlow': (char['finalBlow'] == 1)})
            # Sort after inflicted damage
            attackerDetails.sort(key=lambda x: x['damageDone'], reverse=True)

            # Add ship type names to attackerDetails
            cached = self.getCache('https://api.eveonline.com/eve/TypeName.xml.aspx',
                                   params={'ids': ','.join(map(str, set([attacker['shipTypeID'] for attacker in attackerDetails])))})
            if not cached:
                r = requests.post('https://api.eveonline.com/eve/TypeName.xml.aspx',
                                  data={'ids': ','.join(map(str, set([attacker['shipTypeID'] for attacker in attackerDetails])))},
                                  headers={'User-Agent': 'VM JabberBot'},
                                  timeout=3)
                if r.status_code != 200 or r.encoding != 'utf-8':
                    return 'The TypeName-API returned error code <b>{!s}</b> or the XML encoding is broken.'.format(r.status_code)
                xml = ET.fromstring(r.text)
                self.setCache('https://api.eveonline.com/eve/TypeName.xml.aspx',
                              doc=str(r.text),
                              expiry=int(calendar.timegm(time.strptime(xml[2].text, '%Y-%m-%d %H:%M:%S'))),
                              params={'ids': ','.join(map(str, set([attacker['shipTypeID'] for attacker in attackerDetails])))})
            else:
                xml = ET.fromstring(cached)
            for char in attackerDetails:
                row = xml.find(".//*[@typeID='"+str(char['shipTypeID'])+"']")
                char['shipTypeName'] = str(row.attrib['typeName'])

            # Print attackerDetails
            for (idx, char) in enumerate(attackerDetails[:5]):
                if char['characterName'] != '':
                    reply += '<b>{}</b> did <b>{:,} damage</b> flying a {} (<i>{:,.2%} of total damage</i>)'.format(
                        char['characterName'], char['damageDone'], char['shipTypeName'], char['damageDone']/float(victim['damageTaken']))
                    reply += (' and scored the <b>final blow</b>' if char['finalBlow'] else '')
                    reply += '<br />'
                else:
                    reply += '<b>{}\'s POS</b> did <b>{:,} damage</b> (<i>{:,.2%} of total damage</i>)'.format(
                        char['corporationName'], char['damageDone'], char['damageDone']/float(victim['damageTaken']))
                    reply += (' and scored the <b>final blow</b>' if char['finalBlow'] else '')
                    reply += '<br />'

            # Print final blow if not already included
            if "final blow" not in reply:
                char = [char for char in attackerDetails if char['finalBlow']][0]
                if char['characterName'] != '':
                    reply += '<b>{}</b> did <b>{:,} damage</b> flying a {} (<i>{:,.2%} of total damage</i>)'.format(
                        char['characterName'], char['damageDone'], char['shipTypeName'], char['damageDone']/float(victim['damageTaken']))
                    reply += (' and scored the <b>final blow</b>' if char['finalBlow'] else '')
                    reply += '<br />'
                else:
                    reply += '<b>{}\'s POS</b> did <b>{:,} damage</b> (<i>{:,.2%} of total damage</i>)'.format(
                        char['corporationName'], char['damageDone'], char['damageDone']/float(victim['damageTaken']))
                    reply += (' and scored the <b>final blow</b>' if char['finalBlow'] else '')
                    reply += '<br />'

            reply = reply[:-6]
        except requests.exceptions.RequestException as e:
            return 'There is a problem with the API server. Can\'t connect to the server.'
        except ValueError as e:
            return 'WTF, 0 damage killmail?'
        return reply

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
        try:
            conn = sqlite3.connect("api.cache")
            cur = conn.cursor()

            if len(params) == 0:
                cur.execute(
                    '''SELECT response
                       FROM cache
                       WHERE path = :path
                        AND expiry > :expiry;''',
                    {"path": path,
                     "expiry": time.time()})
                res = cur.fetchall()
                cur.close()
                conn.close()
                if len(res) == 0 or len(res) > 1:
                    return None
                return res[0][0]

            paramlist = ""
            for val in params.values():
                paramlist += val + "+"
            params = paramlist[:-1]
            cur.execute(
                '''SELECT response
                   FROM cache
                   WHERE path = :path
                    AND params = :params
                    AND expiry > :expiry;''',
                {"path": path,
                 "params": params,
                 "expiry": int(time.time())})
            res = cur.fetchall()
            cur.close()
            conn.close()
            if len(res) != 1:
                return None
            return res[0][0]
        except:
            return None

    def setCache(self, path, doc, expiry, params=dict()):
        try:
            conn = sqlite3.connect("api.cache")
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS metadata
                  (type VARCHAR(255) NOT NULL UNIQUE,
                  value INT NOT NULL);''')

            cur.execute('''
                SELECT value
                  FROM metadata
                  WHERE type='version';''')
            res = cur.fetchall()
            if len(res) == 1 and res[0][0] != self.cache_version:
                cur.execute("DROP TABLE cache;")
            conn.commit()

            cur.execute(
                '''INSERT OR REPLACE INTO metadata
                   VALUES (:type, :version);''',
                {"type": "version",
                 "version": self.cache_version})
            cur.execute(
                '''CREATE TABLE IF NOT EXISTS cache(
                    path VARCHAR(255) NOT NULL,
                    params VARCHAR(255),
                    response TEXT NOT NULL,
                    expiry INT
                   );''')
            cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS
                           Query ON cache (path, params);''')
            cur.execute(
                '''DELETE FROM cache
                   WHERE expiry <= :expiry;''',
                {"expiry": int(time.time())})

            if len(params) == 0:
                cur.execute(
                    '''INSERT INTO cache
                       VALUES (:path, :params, :response, :expiry);''',
                    {"path": path,
                     "params": "",
                     "response": doc,
                     "expiry": expiry})
                conn.commit()
                cur.close()
                conn.close()
                return True

            # Fix for params (dict) in table
            paramlist = ""
            for val in params.values():
                paramlist += val + "+"
            params = paramlist[:-1]
            cur.execute(
                '''INSERT INTO cache
                   VALUES (:path, :params, :response, :expiry);''',
                {"path": path,
                 "params": params,
                 "response": doc,
                 "expiry": expiry})
            conn.commit()
            cur.close()
            conn.close()
            return True
        except:
            return False
