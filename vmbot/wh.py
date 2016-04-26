from .jabberbot import botcmd

from os import path
import shlex
import sqlite3

from .helpers.files import WH_DB, STATICDATA_DB
from .helpers.exceptions import DBError



class Wormhole(object):
    WH_VERSION = 2

    def __db_connection(self):
        conn = sqlite3.connect(WH_DB)
        conn.row_factory = sqlite3.Row
        return conn

    def __create_db_schema(self):
        conn = self.__db_connection()

        conn.execute(
            """CREATE TABLE IF NOT EXISTS metadata (
                 type TEXT NOT NULL UNIQUE,
                 value TEXT NOT NULL
               );"""
        )

        res = conn.execute(
            """SELECT value
               FROM metadata
               WHERE type = "version";"""
        ).fetchall()
        if res and int(res[0][0]) != self.WH_VERSION:
            raise DBError("Tell {} to update the WH database!".format(", ".join(self.admins)))

        conn.execute(
            """INSERT OR REPLACE INTO metadata
               VALUES ("version", :version);""",
            {'version': self.WH_VERSION}
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS connections (
                 ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                 SRC INTEGER NOT NULL,
                 `SRC-SIG` TEXT NOT NULL,
                 DEST INTEGER NOT NULL,
                 `DEST-SIG` TEXT NOT NULL,
                 expiry TEXT NOT NULL,
                 author TEXT NOT NULL,
                 created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
               );"""
        )
        conn.commit()

    @botcmd
    def wh(self, mess, args):
        """list - Shows all WH connections (equivalent to filter TTL 0)

        filter "<type>" "<value>" - Filters the list of available WH connections
        |-> type: Either "system" or "TTL"
        +-> value: System/region name or a minimum TTL in hours
        add "<src>" "<src-sig>" "<dest>" "<dest-sig>" "<TTL>" - Adds a new connection
        |-> src/dest: Source/destination systems the WH connects
        |-> src-sig/dest-sig: Signature-IDs in the source/destination systems (eg WQG-828)
        +-> TTL: Minimum number of hours left before the WH closes
        stats - Shows a list of scanners and how many WHs they have scanned during the last 30 days
        """
        argsList = shlex.split(args)
        if argsList:
            cmd = argsList.pop(0).upper()
        else:
            return "Requires one of list, filter, add or stats as an argument"
        argc = len(argsList)

        if cmd == "LIST" and argc == 0:
            return self.wh_list(mess)
        elif cmd == "FILTER" and argc == 2:
            return self.wh_filter(mess, *argsList)
        elif cmd == "ADD" and argc == 5:
            return self.wh_add(mess, *argsList)
        elif cmd == "STATS" and argc == 0:
            return self.wh_stats(mess)
        else:
            return "wh {} is not an accepted command".format(args)

    def _getActiveConnections(self):
        return self.__db_connection().execute(
            """SELECT SRC, `SRC-SIG`, DEST, `DEST-SIG`, author,
                      (JULIANDAY(expiry) - JULIANDAY("now")) * 24 AS TTL
               FROM connections
               WHERE expiry > DATETIME("now");"""
        ).fetchall()

    def wh_list(self, mess, data=None):
        if data is None:
            try:
                data = self._getActiveConnections()
            except sqlite3.OperationalError:
                return "Error: Data is missing"

        connections = []
        connectionDetails = "{} ({} | {}) <-> {} ({} | {}) | About {:.0f}h left | Scanned by {}"
        for connection in data:
            src = self.getSolarSystemData(connection['SRC'])
            dest = self.getSolarSystemData(connection['DEST'])
            connections.append(connectionDetails.format(
                src['solarSystemName'], connection['SRC-SIG'], src['regionName'],
                dest['solarSystemName'], connection['DEST-SIG'], dest['regionName'],
                float(connection['TTL']), connection['author']
            ))

        if connections:
            return "<br />".join(connections)

        return "No connections found"

    def wh_filter(self, mess, filterType, filterVal):
        filterType, filterVal = filterType.upper(), filterVal.upper()
        if filterType == "TTL":
            try:
                filterVal = float(filterVal)
            except:
                return "value must be a floating point number when used with TTL"

        try:
            data = self._getActiveConnections()
        except sqlite3.OperationalError:
            return "Error: Data is missing"

        allConnections = []
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
                'author': connection['author']
            })

        if filterType == "TTL":
            filteredConnections = [wh for wh in allConnections if wh['TTL'] >= filterVal]
        elif filterType == "SYSTEM":
            filteredConnections = [wh for wh in allConnections
                                   if filterVal in (wh['SRC-System'].upper(),
                                                    wh['SRC-Region'].upper(),
                                                    wh['DEST-System'].upper(),
                                                    wh['DEST-Region'].upper())]
        else:
            filteredConnections = allConnections

        return self.wh_list(mess, filteredConnections)

    def wh_add(self, mess, src, srcSIG, dest, destSIG, TTL):
        try:
            TTL = float(TTL)
        except ValueError:
            return "TTL must be a floating point number"

        try:
            self.__create_db_schema()
        except DBError as e:
            return str(e)

        conn = sqlite3.connect(STATICDATA_DB)
        srcSystems = conn.execute(
            """SELECT solarSystemID, solarSystemName
               FROM mapSolarSystems
               WHERE solarSystemName LIKE :name;""",
            {'name': "%{}%".format(src)}
        ).fetchall()
        destSystems = conn.execute(
            """SELECT solarSystemID, solarSystemName
               FROM mapSolarSystems
               WHERE solarSystemName LIKE :name;""",
            {'name': "%{}%".format(dest)}
        ).fetchall()
        conn.close()

        if not srcSystems or not destSystems:
            return "Can't find matching systems!"

        # Sort by length of name so that the most similar item is first
        srcSystems.sort(cmp=lambda x, y: cmp(len(x), len(y)), key=lambda x: x[1])
        destSystems.sort(cmp=lambda x, y: cmp(len(x), len(y)), key=lambda x: x[1])

        conn = self.__db_connection()
        conn.execute(
            """INSERT INTO `connections` (SRC, `SRC-SIG`, DEST, `DEST-SIG`, expiry, author)
               VALUES (:srcID, :srcSIG, :destID, :destSIG,
                       DATETIME("now", "{:+} hours"), :author);""".format(TTL),
            {'srcID': srcSystems[0][0], 'srcSIG': srcSIG,
             'destID': destSystems[0][0], 'destSIG': destSIG,
             'author': self.get_uname_from_mess(mess)}
        )
        conn.commit()
        conn.close()

        return "Wormhole from {} to {} was added by {}".format(srcSystems[0][1], destSystems[0][1],
                                                               self.get_uname_from_mess(mess))

    def wh_stats(self, mess):
        conn = self.__db_connection()

        try:
            data = conn.execute("""SELECT author, COUNT(*) as scannedWHs
                                   FROM connections
                                   WHERE created BETWEEN DATETIME("now", "-1 month")
                                                     AND DATETIME("now")
                                   GROUP BY author;""").fetchall()
        except sqlite3.OperationalError:
            return "Error: Data is missing"

        if not data:
            return "No connections were added during the last month"

        stats = ["{}: {} WH(s)".format(scanner['author'], scanner['scannedWHs'])
                 for scanner in data]

        return "<br />".join(stats)
