# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import json
import xml.etree.ElementTree as ET
import logging
import traceback

import requests

from .exceptions import NoCacheError, APIError, APIStatusError, APIRequestError
from . import database as db
from ..models.cache import parse_http_cache, parse_xml_cache, HTTPCacheObject, ESICacheObject
from . import staticdata
from .format import format_tickers
from ..models import ISK

import config


def get_tickers(corporationID, allianceID):
    """Resolve corporationID/allianceID to their respective ticker(s)."""
    corp_ticker = None
    if corporationID:
        corp_ticker = "ERROR"
        try:
            corp = request_esi("/v3/corporations/{}/", (corporationID,))
        except APIError:
            pass
        else:
            corp_ticker = corp['ticker']
            allianceID = allianceID or corp.get('alliance_id', None)

    alliance_ticker = None
    if allianceID:
        alliance_ticker = "ERROR"
        try:
            ally = request_esi("/v2/alliances/{}/", (allianceID,))
        except APIError:
            pass
        else:
            alliance_ticker = ally['ticker']

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

    return ("{} {} | {} ({:,} point(s)) | {:.2f} ISK | "
            "{} ({}) | {} participant(s) ({:,} damage) | {}").format(
        victim['characterName'] or victim['corporationName'],
        format_tickers(corp_ticker, alliance_ticker),
        staticdata.typeName(victim['shipTypeID']), killdata['zkb']['points'],
        ISK(killdata['zkb']['totalValue']),
        system['solarSystemName'], system['regionName'],
        len(killdata['attackers']), victim['damageTaken'],
        killdata['killTime']
    )


def request_rest(url, params=None, data=None, headers=None, timeout=3, method="GET"):
    session = db.Session()
    res = HTTPCacheObject.get(session, url, params=params, data=data, headers=headers)

    if res is None:
        r = request_api(url, params, data, headers, timeout, method)
        res = r.content

        try:
            expiry = parse_http_cache(r.headers)
        except NoCacheError:
            pass
        else:
            HTTPCacheObject(url, r.content, expiry, params=params,
                            data=data, headers=headers).save(session)

    session.close()
    return json.loads(res.decode("utf-8"))


def request_esi(route, fmt=(), params=None, data=None, headers=None,
                timeout=3, method="GET", with_head=False):
    url = (config.ESI['base_url'] if route.startswith('/') else "") + route.format(*fmt)

    if params is None:
        params = {}
    params['datasource'] = config.ESI['datasource']
    params['language'] = config.ESI['lang']

    session = db.Session()
    r = ESICacheObject.get(session, url, params=params, data=data, headers=headers)

    if r is None:
        r = request_api(url, params, data, headers, timeout, method)

        if 'warning' in r.headers:
            # Versioned endpoint is outdated (199) or deprecated (299)
            kw = "outdated" if r.headers['warning'][:3] == "199" else "deprecated"
            trace = "".join(traceback.format_stack(limit=3)[:-1])

            warn = 'Route "{}" is {}'.format(route, kw)
            warn += "\nResponse header: warning: " + r.headers['warning']
            warn += "\nTraceback (most recent call last):\n" + trace
            logging.getLogger(__name__ + ".esi").warning(warn, extra={'gh_labels': ["esi-warning"]})

        try:
            expiry = parse_http_cache(r.headers)
        except NoCacheError:
            pass
        else:
            ESICacheObject(url, r, expiry, params=params, data=data, headers=headers).save(session)

    session.close()
    if with_head:
        return r.json(), r.headers
    return r.json()


def request_xml(url, params=None, data=None, headers=None, timeout=3, method="POST"):
    session = db.Session()
    res = HTTPCacheObject.get(session, url, params=params, data=data, headers=headers)

    if res is None:
        r = request_api(url, params, data, headers, timeout, method)
        res = ET.fromstring(r.content)

        try:
            expiry = parse_xml_cache(res)
        except NoCacheError:
            pass
        else:
            HTTPCacheObject(url, r.content, expiry, params=params,
                            data=data, headers=headers).save(session)
    else:
        res = ET.fromstring(res)

    session.close()
    return res.find("result")


def request_api(url, params=None, data=None, headers=None, timeout=3, method="GET"):
    if headers is None:
        headers = {}
    headers['User-Agent'] = "XVMX JabberBot"

    try:
        r = requests.request(method, url, params=params, data=data,
                             headers=headers, timeout=timeout)
        r.raise_for_status()
    except requests.HTTPError as e:
        raise APIStatusError("API returned error code {}".format(e.response.status_code))
    except requests.RequestException as e:
        raise APIRequestError("Error while connecting to API: {}".format(e))

    return r
