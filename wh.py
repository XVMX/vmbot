from jabberbot import botcmd

import shlex
import sqlite3


class Wormhole(object):
    wh_version = 1

    def __db_connection(self):
        conn = sqlite3.connect("wh.sqlite")
        conn.row_factory = sqlite3.Row
        return conn

    def __db_schema(self):
        conn = self.__db_connection()
        cur = conn.cursor()

        cur.execute(
            '''CREATE TABLE IF NOT EXISTS `metadata` (
                `type` TEXT NOT NULL UNIQUE,
                `value` INT NOT NULL
               );''')
        conn.commit()
        cur.execute(
            '''SELECT `value`
               FROM `metadata`
               WHERE `type` = 'version';''')
        res = cur.fetchall()
        if res and res[0][0] != self.wh_version:
            return "Tell {} to update the WH database".format(", ".join(self.admins))

        cur.execute(
            '''INSERT OR REPLACE INTO `metadata` (`type`, `value`)
               VALUES (:type, :version);''',
            {"type": "version",
             "version": self.wh_version})
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS `connections` (
                `ID` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                `SRC` INTEGER NOT NULL,
                `SRC-SIG` TEXT NOT NULL,
                `DEST` INTEGER NOT NULL,
                `DEST-SIG` TEXT NOT NULL,
                `Expiry` TEXT NOT NULL,
                `Author` TEXT NOT NULL,
                `created` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
               );''')
        conn.commit()

    @botcmd
    def wh(self, mess, args):
        '''list - Shows all WH connections

filter "<type>" "<value>" - Filters the list of available WH connections
  type: One of "src", "dest" or "TTL"
  value: Either the system or region name for "src" and "dest" or a minimum TTL in hours
add "<src>" "<src-sig>" "<dest>" "<dest-sig>" "<TTL>" - Adds a new connection (TTL in hours)
stats - Shows a list of scanners and how many WHs they have scanned during the last month'''
        args = shlex.split(args.strip())
        if args:
            cmd = args[0].upper()
        else:
            return "Requires one of list, filter, add or stats as an argument"
        argc = len(args)

        if cmd == "LIST" and argc == 1:
            return self.wh_list(mess)
        elif cmd == "FILTER" and argc == 3:
            return self.wh_filter(mess, args[1].upper(), args[2].upper())
        elif cmd == "ADD" and argc == 6:
            return self.wh_add(mess, args[1], args[2], args[3], args[4], args[5])
        elif cmd == "STATS" and argc == 1:
            return self.wh_stats(mess,)
        else:
            return "wh {} is not an accepted command".format(" ".join(args))

    def wh_getActiveConnections(self):
        conn = self.__db_connection()
        cur = conn.cursor()

        cur.execute('''SELECT `SRC`, `SRC-SIG`, `DEST`, `DEST-SIG`, `Author`,
                              (JULIANDAY(`Expiry`) - JULIANDAY('now')) * 24 AS `TTL`
                       FROM connections
                       WHERE `Expiry` > DATETIME('now');''')

        return cur.fetchall()

    def wh_list(self, mess, data=None):
        if data is None:
            try:
                data = self.wh_getActiveConnections()
            except sqlite3.OperationalError:
                return "Error: Data is missing"

        res = ""
        for connection in data:
            src = self.getSolarSystemData(connection['SRC'])
            dest = self.getSolarSystemData(connection['DEST'])
            res += "{} ({} | {}) -> {} ({} | {}) | About {:.0f}h left | Scanned by {}".format(
                src['solarSystemName'],
                connection['SRC-SIG'],
                src['regionName'],
                dest['solarSystemName'],
                connection['DEST-SIG'],
                dest['regionName'],
                float(connection['TTL']),
                connection['Author']
            )
            res += "<br />"

        if data:
            return res[:-6]

        return "No connections found"

    def wh_filter(self, mess, filterType, filterVal):
        try:
            data = self.wh_getActiveConnections()
        except sqlite3.OperationalError:
            return "Error: Data is missing"

        allConnections = list()
        for connection in data:
            src = self.getSolarSystemData(connection['SRC'])
            dest = self.getSolarSystemData(connection['DEST'])
            allConnections.append({
                'SRC': connection['SRC'],
                'SRC-System': src['solarSystemName'],
                'SRC-Region': src['regionName'],
                'SRC-SIG': connection['SRC-SIG'],
                'DEST': connection['DEST'],
                'DEST-System': dest['solarSystemName'],
                'DEST-Region': dest['regionName'],
                'DEST-SIG': connection['DEST-SIG'],
                'TTL': float(connection['TTL']),
                'Author': connection['Author']
            })

        filteredConnections = list()
        if filterType == "SRC":
            filteredConnections = [wh for wh in allConnections
                                   if filterVal in (wh['SRC-System'].upper(),
                                                    wh['SRC-Region'].upper())]
        elif filterType == "DEST":
            filteredConnections = [wh for wh in allConnections
                                   if filterVal in (wh['DEST-System'].upper(),
                                                    wh['DEST-Region'].upper())]
        elif filterType == "TTL":
            filteredConnections = [wh for wh in allConnections if wh['TTL'] >= float(filterVal)]

        return self.wh_list(mess, filteredConnections)

    def wh_add(self, mess, src, srcSIG, dest, destSIG, TTL):
        res = self.__db_schema()
        if res:
            return res

        conn = sqlite3.connect('staticdata.sqlite')
        cur = conn.cursor()
        cur.execute(
            '''SELECT solarSystemID, solarSystemName
               FROM mapSolarSystems
               WHERE solarSystemName LIKE :name;''',
            {'name': "%{}%".format(src)})
        srcSystems = cur.fetchall()
        cur.execute(
            '''SELECT solarSystemID, solarSystemName
               FROM mapSolarSystems
               WHERE solarSystemName LIKE :name;''',
            {'name': "%{}%".format(dest)})
        destSystems = cur.fetchall()
        if not srcSystems or not destSystems:
            return "Can't find matching systems!"
        cur.close()
        conn.close()

        # Sort by length of name so that the most similar item is first
        srcSystems.sort(lambda x, y: cmp(len(x[1]), len(y[1])))
        destSystems.sort(lambda x, y: cmp(len(x[1]), len(y[1])))

        conn = self.__db_connection()
        cur = conn.cursor()

        cur.execute(
            '''INSERT INTO `connections` (`SRC`, `SRC-SIG`, `DEST`, `DEST-SIG`, `Expiry`, `Author`)
               VALUES (:srcID, :srcSIG, :destID, :destSIG,
                       DATETIME('now', '+{} hours'), :author);'''.format(TTL),
            {'srcID': srcSystems[0][0],
             'srcSIG': srcSIG,
             'destID': destSystems[0][0],
             'destSIG': destSIG,
             'author': str(self.get_uname_from_mess(mess))})
        conn.commit()

        return "Wormhole from {} to {} was added by {}".format(srcSystems[0][0], destSystems[0][0],
                                                               self.get_uname_from_mess(mess))

    def wh_stats(self, mess):
        conn = self.__db_connection()
        cur = conn.cursor()

        try:
            cur.execute('''SELECT `Author`, COUNT(*) as `scannedWHs`
                           FROM connections
                           WHERE `created` BETWEEN DATETIME('now', '-1 month', 'start of month')
                             AND DATETIME('now', 'start of month')
                           GROUP BY `Author`;''')
        except sqlite3.OperationalError:
            return "Error: Data is missing"
        data = cur.fetchall()

        if not data:
            return "No connections available"

        res = ""
        for scanner in data:
            res += "{}: {} WHs".format(scanner['Author'], scanner['scannedWHs'])
            res += "<br />"

        return res[:-6]
