# coding: utf-8

import json
import xml.etree.ElementTree as ET
import sqlite3

import requests

from .files import STATICDATA_DB
from .exceptions import APIError, NoCacheError
from . import database as db
from ..models.cache import parse_cache_control, parse_xml_cache, HTTPCacheObject


def get_typeName(typeID):
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


def get_solarSystemData(solarSystemID):
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


def get_tickers(corporationID, allianceID):
    """Resolve corpID/allianceID to their respective ticker(s)."""
    corp_ticker = None
    if corporationID:
        corp_ticker = "ERROR"
        try:
            xml = post_xml_endpoint(
                "https://api.eveonline.com/corp/CorporationSheet.xml.aspx",
                params={'corporationID': corporationID}
            ).find("result")

            corp_ticker = xml.find("ticker").text
            allianceID = allianceID or int(xml.find("allianceID").text) or None
        except Exception:
            pass

    alliance_ticker = None
    if allianceID:
        alliance_ticker = "ERROR"
        try:
            alliance_ticker = post_xml_endpoint(
                "https://api.eveonline.com/eve/AllianceList.xml.aspx",
                params={'version': 1}
            ).find("result/rowset/row[@allianceID='{}']".format(allianceID)).attrib['shortName']
        except Exception:
            pass

    return corp_ticker, alliance_ticker


def get_rest_endpoint(url, params=None, timeout=3):
    session = db.Session()
    res = HTTPCacheObject.get(url, session, params=params)
    if res is None:
        r = request_api(url, params, timeout, method="GET")
        res = r.content

        try:
            expiry = parse_cache_control(r.headers['Cache-Control'])
        except (KeyError, NoCacheError):
            pass
        else:
            HTTPCacheObject(url, r.content, expiry, params=params).save(session)

    return json.loads(res.decode("utf-8"))


def post_xml_endpoint(url, params=None, timeout=3):
    session = db.Session()
    res = HTTPCacheObject.get(url, session, params=params)
    if res is None:
        r = request_api(url, params, timeout, method="POST")
        xml = ET.fromstring(r.content)

        try:
            expiry = parse_xml_cache(xml)
        except NoCacheError:
            pass
        else:
            HTTPCacheObject(url, r.content, expiry, params=params).save(session)

        return xml

    return ET.fromstring(res)


def request_api(url, params=None, timeout=3, method="GET"):
    headers = {'User-Agent': "XVMX JabberBot"}

    try:
        if method in ("GET", "HEAD"):
            r = requests.request(method, url, params=params, headers=headers, timeout=timeout)
        else:
            r = requests.request(method, url, data=params, headers=headers, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise APIError("Error while connecting to an API: {}".format(e))
    if r.status_code != 200:
        raise APIError("An API returned error code {}".format(r.status_code))

    return r
