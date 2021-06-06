# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import sqlite3

from .files import STATICDATA_DB


def type_name(type_id):
    """Resolve a type_id to its name."""
    conn = sqlite3.connect(STATICDATA_DB)
    item = conn.execute(
        """SELECT typeID, typeName
           FROM invTypes
           WHERE typeID = :id;""",
        {'id': type_id}
    ).fetchone()
    conn.close()

    if not item:
        return "{Failed to load}"
    return item[1]


def search_market_types(term):
    """Resolve a search term to types that are listed on the market."""
    # Sort by name length so that the most similar item is first
    conn = sqlite3.connect(STATICDATA_DB)
    items = conn.execute(
        """SELECT typeID, typeName
           FROM invTypes
           WHERE typeName LIKE :name
             AND published
             AND marketGroupID IS NOT NULL
           ORDER BY LENGTH(typeName) ASC;""",
        {'name': "%{}%".format(term)}
    ).fetchall()
    conn.close()

    return items


def region_data(region_id):
    """Resolve a region_id to its data."""
    conn = sqlite3.connect(STATICDATA_DB)
    region = conn.execute(
        """SELECT regionID, regionName
           FROM mapRegions
           WHERE regionID = :id;""",
        {'id': region_id}
    ).fetchone()
    conn.close()

    if not region:
        return {'region_id': 0, 'region_name': "{Failed to load}"}
    return {'region_id': region[0], 'region_name': region[1]}


def system_data(system_id):
    """Resolve a system_id to its data."""
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
        {'id': system_id}
    ).fetchone()
    conn.close()

    if not system:
        return {'system_id': 0, 'system_name': "{Failed to load}",
                'constellation_id': 0, 'constellation_name': "{Failed to load}",
                'region_id': 0, 'region_name': "{Failed to load}"}
    return {'system_id': system[0], 'system_name': system[1],
            'constellation_id': system[2], 'constellation_name': system[3],
            'region_id': system[4], 'region_name': system[5]}


def item_name(item_id):
    """Resolve an item_id to its name."""
    conn = sqlite3.connect(STATICDATA_DB)
    item = conn.execute(
        """SELECT itemID, itemName
           FROM invNames
           WHERE itemID = :id;""",
        {'id': item_id}
    ).fetchone()
    conn.close()

    if not item:
        return "{Failed to load}"
    return item[1]


def faction_name(faction_id):
    """Resolve a faction_id to its name."""
    conn = sqlite3.connect(STATICDATA_DB)
    faction = conn.execute(
        """SELECT factionID, factionName
           FROM chrFactions
           WHERE factionID = :id;""",
        {'id': faction_id}
    ).fetchone()
    conn.close()

    if not faction:
        return "{Failed to load}"
    return faction[1]


def system_stations(system_id):
    """Resolve a system_id to all station_ids contained within the system."""
    conn = sqlite3.connect(STATICDATA_DB)
    stations = conn.execute(
        """SELECT stationID
           FROM staStations
           WHERE solarSystemID = :id;""",
        {'id': system_id}
    ).fetchall()
    conn.close()

    return [r[0] for r in stations]
