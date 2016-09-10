# coding: utf-8

import sqlite3

from .files import STATICDATA_DB


def typeName(typeID):
    """Resolve a typeID to its name."""
    conn = sqlite3.connect(STATICDATA_DB)
    item = conn.execute(
        """SELECT typeID, typeName
           FROM invTypes
           WHERE typeID = :id;""",
        {'id': typeID}
    ).fetchone()
    conn.close()

    if not item:
        return "{Failed to load}"
    return item[1]


def solarSystemData(solarSystemID):
    """Resolve a solarSystemID to its data."""
    conn = sqlite3.connect(STATICDATA_DB)
    system = conn.execute(
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
    ).fetchone()
    conn.close()

    if not system:
        return {'solarSystemID': 0, 'solarSystemName': "{Failed to load}",
                'constellationID': 0, 'constellationName': "{Failed to load}",
                'regionID': 0, 'regionName': "{Failed to load}"}
    return {'solarSystemID': system[0], 'solarSystemName': system[1],
            'constellationID': system[2], 'constellationName': system[3],
            'regionID': system[4], 'regionName': system[5]}
