# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import threading
from contextlib import contextmanager
import sqlite3

import cachetools.func

from .files import STATICDATA_DB

_sde_lock = threading.Lock()


@contextmanager
def _get_sde_conn():
    """Retrieve or create and lock the global sqlite SDE connection."""
    global _sde_conn
    with _sde_lock:
        try:
            _sde_conn
        except NameError:
            _sde_conn = sqlite3.connect(STATICDATA_DB)
        yield _sde_conn


@cachetools.func.lru_cache(maxsize=128)
def type_name(type_id):
    """Resolve a type_id to its name."""
    with _get_sde_conn() as conn:
        type = conn.execute(
            """SELECT typeName
               FROM invTypes
               WHERE typeID = :id;""",
            {'id': type_id}
        ).fetchone()

    return type[0] if type else "{Failed to load}"


def search_market_types(term):
    """Resolve a search term to types that are listed on the market."""
    with _get_sde_conn() as conn:
        # Sort by name length so that the most similar item is first
        return conn.execute(
            """SELECT typeID, typeName
               FROM invTypes
               WHERE typeName LIKE :name
                 AND published
                 AND marketGroupID IS NOT NULL
               ORDER BY LENGTH(typeName) ASC;""",
            {'name': "%{}%".format(term)}
        ).fetchall()


@cachetools.func.lru_cache(maxsize=4)
def region_data(region_id):
    """Resolve a region_id to its data."""
    with _get_sde_conn() as conn:
        region = conn.execute(
            """SELECT regionName
               FROM mapRegions
               WHERE regionID = :id;""",
            {'id': region_id}
        ).fetchone()

    if not region:
        return {'region_id': 0, 'region_name': "{Failed to load}"}
    return {'region_id': region_id, 'region_name': region[0]}


@cachetools.func.lru_cache(maxsize=128)
def system_data(system_id):
    """Resolve a system_id to its data."""
    with _get_sde_conn() as conn:
        system = conn.execute(
            """SELECT solarSystemName,
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

    if not system:
        return {'system_id': 0, 'system_name': "{Failed to load}",
                'constellation_id': 0, 'constellation_name': "{Failed to load}",
                'region_id': 0, 'region_name': "{Failed to load}"}
    return {'system_id': system_id, 'system_name': system[0],
            'constellation_id': system[1], 'constellation_name': system[2],
            'region_id': system[3], 'region_name': system[4]}


@cachetools.func.lru_cache(maxsize=64)
def item_name(item_id):
    """Resolve an item_id to its name."""
    with _get_sde_conn() as conn:
        item = conn.execute(
            """SELECT itemName
               FROM invNames
               WHERE itemID = :id;""",
            {'id': item_id}
        ).fetchone()

    return item[0] if item else "{Failed to load}"


@cachetools.func.lru_cache(maxsize=None)
def faction_name(faction_id):
    """Resolve a faction_id to its name."""
    with _get_sde_conn() as conn:
        faction = conn.execute(
            """SELECT factionName
               FROM chrFactions
               WHERE factionID = :id;""",
            {'id': faction_id}
        ).fetchone()

    return faction[0] if faction else "{Failed to load}"


def system_stations(system_id):
    """Resolve a system_id to all station_ids contained within the system."""
    with _get_sde_conn() as conn:
        stations = conn.execute(
            """SELECT stationID
               FROM staStations
               WHERE solarSystemID = :id;""",
            {'id': system_id}
        ).fetchall()

    return [r[0] for r in stations]
