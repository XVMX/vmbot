# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import json
import xml.etree.ElementTree as ET

import requests

from .exceptions import APIError, NoCacheError
from . import database as db
from ..models.cache import parse_cache_control, parse_xml_cache, HTTPCacheObject
from . import staticdata
from .format import format_tickers
from ..models import ISK


def get_tickers(corporationID, allianceID):
    """Resolve corporationID/allianceID to their respective ticker(s)."""
    corp_ticker = None
    if corporationID:
        corp_ticker = "ERROR"
        try:
            xml = request_xml(
                "https://api.eveonline.com/corp/CorporationSheet.xml.aspx",
                params={'corporationID': corporationID}
            )

            corp_ticker = xml.find("ticker").text
            if allianceID is None:
                allianceID = int(xml.find("allianceID").text) or None
        except (APIError, AttributeError):
            pass

    alliance_ticker = None
    if allianceID:
        alliance_ticker = "ERROR"
        try:
            alliance_ticker = request_xml(
                "https://api.eveonline.com/eve/AllianceList.xml.aspx",
                params={'version': 1}
            ).find("rowset/row[@allianceID='{}']".format(allianceID)).attrib['shortName']
        except (APIError, AttributeError):
            pass

    return corp_ticker, alliance_ticker


def zbot(killID):
    """Create a compact overview of a zKB killmail."""
    url = "https://zkillboard.com/api/killID/{}/no-items/".format(killID)
    try:
        killdata = request_rest(url)
    except APIError as e:
        return unicode(e)

    if not killdata:
        return "Failed to load data for https://zkillboard.com/kill/{}/".format(killID)

    killdata = killdata[0]
    victim = killdata['victim']
    system = staticdata.solarSystemData(killdata['solarSystemID'])
    corp_ticker, alliance_ticker = get_tickers(victim['corporationID'], victim['allianceID'])

    # Compact header
    return ("{} {} | {} ({:,} point(s)) | {:.2f} ISK | "
            "{} ({}) | {} participants ({:,} damage) | {}").format(
        victim['characterName'] or victim['corporationName'],
        format_tickers(corp_ticker, alliance_ticker),
        staticdata.typeName(victim['shipTypeID']), killdata['zkb']['points'],
        ISK(killdata['zkb']['totalValue']),
        system['solarSystemName'], system['regionName'],
        len(killdata['attackers']), victim['damageTaken'],
        killdata['killTime']
    )


def request_rest(url, params=None, headers=None, timeout=3, method="GET"):
    session = db.Session()
    res = HTTPCacheObject.get(url, session, params=params, headers=headers)

    if res is None:
        r = request_api(url, params, headers, timeout, method)
        res = r.content

        try:
            expiry = parse_cache_control(r.headers['Cache-Control'])
        except (KeyError, NoCacheError):
            pass
        else:
            HTTPCacheObject(url, r.content, expiry, params=params, headers=headers).save(session)

    session.close()
    return json.loads(res.decode("utf-8"))


def request_xml(url, params=None, headers=None, timeout=3, method="POST"):
    session = db.Session()
    res = HTTPCacheObject.get(url, session, params=params, headers=headers)

    if res is None:
        r = request_api(url, params, headers, timeout, method)
        res = ET.fromstring(r.content)

        try:
            expiry = parse_xml_cache(res)
        except NoCacheError:
            pass
        else:
            HTTPCacheObject(url, r.content, expiry, params=params, headers=headers).save(session)
    else:
        res = ET.fromstring(res)

    session.close()
    return res.find("result")


def request_api(url, params=None, headers=None, timeout=3, method="GET"):
    if headers is None:
        headers = {}
    headers['User-Agent'] = "XVMX JabberBot"

    try:
        if method in ("GET", "HEAD"):
            r = requests.request(method, url, params=params, headers=headers, timeout=timeout)
        else:
            r = requests.request(method, url, data=params, headers=headers, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise APIError("Error while connecting to API: {}".format(e))
    if r.status_code != 200:
        raise APIError("API returned error code {}".format(r.status_code))

    return r
