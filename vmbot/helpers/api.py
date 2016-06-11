# coding: utf-8

import time
from calendar import timegm
import re
import json
import xml.etree.ElementTree as ET
import sqlite3

import requests

from . import cache
from .files import STATICDATA_DB
from .exceptions import APIError


def get_typeName(typeID):
    """Resolve a typeID to its name."""
    conn = sqlite3.connect(STATICDATA_DB)
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


def get_solarSystemData(solarSystemID):
    """Resolve a solarSystemID to its data."""
    conn = sqlite3.connect(STATICDATA_DB)
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


def get_crest_endpoint(url, params=None, timeout=3):
    """Parse JSON document associated with CREST url."""
    cached = cache.get_http(url, params=params)
    if not cached:
        try:
            r = requests.get(url, params=params, headers={'User-Agent': "XVMX JabberBot"},
                             timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise APIError("Error while connecting to CREST: {}".format(e))
        if r.status_code != 200:
            raise APIError("CREST returned error code {}".format(r.status_code))

        res = r.json()
        try:
            expires_in = int(
                re.search("max-age=(\d+)", r.headers['Cache-Control'], re.IGNORECASE).group(1)
            )
        except (KeyError, AttributeError):
            pass
        else:
            cache.set_http(url, doc=r.content, expiry=int(time.time() + expires_in), params=params)
    else:
        res = json.loads(cached)

    return res


def post_xml_endpoint(url, data=None, timeout=3):
    """Parse XML document associated with EVE API url."""
    cached = cache.get_http(url, params=data)
    if not cached:
        try:
            r = requests.post(url, data=data, headers={'User-Agent': "XVMX JabberBot"},
                              timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise APIError("Error while connecting to XML-API: {}".format(e))
        if r.status_code != 200:
            raise APIError("XML-API returned error code {}".format(r.status_code))

        xml = ET.fromstring(r.content)
        cache.set_http(
            url, doc=r.content,
            expiry=int(timegm(time.strptime(xml[2].text, "%Y-%m-%d %H:%M:%S"))),
            params=data
        )
    else:
        xml = ET.fromstring(cached)

    return xml


def get_tickers(corporationID, allianceID):
    """Resolve corpID/allianceID to their respective ticker(s)."""
    corp_ticker = None
    if corporationID:
        corp_ticker = "{Failed to load}"
        try:
            xml = post_xml_endpoint(
                "https://api.eveonline.com/corp/CorporationSheet.xml.aspx",
                data={'corporationID': corporationID}
            )

            corp_ticker = str(xml[1].find("ticker").text)
            allianceID = allianceID or int(xml[1].find("allianceID").text) or None
        except:
            pass

    alliance_ticker = None
    if allianceID:
        alliance_ticker = "{Failed to load}"
        try:
            alliance_ticker = get_crest_endpoint(
                "https://crest-tq.eveonline.com/alliances/{}/".format(allianceID)
            )['shortName']
        except:
            pass

    return corp_ticker, alliance_ticker
