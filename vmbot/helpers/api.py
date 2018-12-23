# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime
import copy
import threading
import json
import logging
import traceback

import requests

from .exceptions import NoCacheError, APIError, APIStatusError, APIRequestError
from . import database as db
from ..models.cache import parse_http_cache, HTTPCacheObject, ESICacheObject
from . import staticdata
from .format import format_tickers
from ..models import ISK

import config

_API_REG = threading.local()


def _get_db_session():
    """Retrieve or create a thread-local SQLAlchemy session."""
    try:
        return _API_REG.db_sess
    except AttributeError:
        _API_REG.db_sess = db.Session()
        return _API_REG.db_sess


def _get_requests_session():
    """Retrieve or create a thread-local requests session."""
    try:
        return _API_REG.req_sess
    except AttributeError:
        _API_REG.req_sess = requests.Session()
        return _API_REG.req_sess


def get_name(id_):
    try:
        return request_esi("/v2/universe/names/", data=json.dumps([id_]),
                           headers={'Content-Type': "application/json"}, method="POST")[0]['name']
    except (APIError, IndexError):
        return "{ERROR}"


def get_tickers(corp_id, ally_id):
    """Resolve corp_id/ally_id to their respective ticker(s)."""
    corp_ticker = None
    if corp_id:
        corp_ticker = "ERROR"
        try:
            corp = request_esi("/v4/corporations/{}/", (corp_id,))
        except APIError:
            pass
        else:
            corp_ticker = corp['ticker']
            ally_id = ally_id or corp.get('alliance_id', None)

    alliance_ticker = None
    if ally_id:
        alliance_ticker = "ERROR"
        try:
            ally = request_esi("/v3/alliances/{}/", (ally_id,))
        except APIError:
            pass
        else:
            alliance_ticker = ally['ticker']

    return corp_ticker, alliance_ticker


def zbot(kill_id):
    """Create a compact overview of a zKB killmail."""
    url = "https://zkillboard.com/api/killID/{}/".format(kill_id)
    try:
        zkb = request_rest(url)
    except APIError as e:
        return unicode(e)

    if not zkb:
        return "Failed to load data for https://zkillboard.com/kill/{}/".format(kill_id)

    zkb = zkb[0]['zkb']
    try:
        killdata = request_esi("/v1/killmails/{}/{}/", (kill_id, zkb['hash']))
    except APIError as e:
        return unicode(e)

    victim = killdata['victim']
    name = get_name(victim.get('character_id', victim['corporation_id']))
    system = staticdata.system_data(killdata['solar_system_id'])
    corp_ticker, alliance_ticker = get_tickers(victim['corporation_id'],
                                               victim.get('alliance_id', None))
    killtime = datetime.strptime(killdata['killmail_time'], "%Y-%m-%dT%H:%M:%SZ")

    return ("{} {} | {} ({:,} point(s)) | {:.2f} ISK | "
            "{} ({}) | {} participant(s) ({:,} damage) | {:%Y-%m-%d %H:%M:%S}").format(
        name, format_tickers(corp_ticker, alliance_ticker),
        staticdata.type_name(victim['ship_type_id']), zkb['points'],
        ISK(zkb['totalValue']), system['system_name'], system['region_name'],
        len(killdata['attackers']), victim['damage_taken'], killtime
    )


def request_rest(url, params=None, data=None, headers=None, timeout=3, method="GET"):
    # url, timeout, and method are immutable
    params, data, headers = copy.copy(params), copy.copy(data), copy.copy(headers)

    session = _get_db_session()
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

    # url (route + fmt), timeout, and method are immutable
    params = {} if params is None else copy.copy(params)
    data, headers = copy.copy(data), copy.copy(headers)

    params['datasource'] = config.ESI['datasource']
    params['language'] = config.ESI['lang']

    session = _get_db_session()
    r = ESICacheObject.get(session, url, params=params, data=data, headers=headers)

    if r is None:
        r = request_api(url, params, data, headers, timeout, method)

        if 'warning' in r.headers:
            # Versioned endpoint is outdated (199) or deprecated (299)
            kw = "outdated" if r.headers['warning'][:3] == "199" else "deprecated"
            trace = "".join(traceback.format_stack(limit=3)[:-1])

            warn = 'Route "{}" is {}'.format(route, kw)
            warn += "\nResponse header: warning: " + r.headers['warning']
            warn += "\nTraceback (most recent call last):\n```\n" + trace + "\n```"
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


def request_api(url, params=None, data=None, headers=None, timeout=3, method="GET"):
    if headers is None:
        headers = {}
    headers['User-Agent'] = "XVMX VMBot (JabberBot)"

    try:
        r = _get_requests_session().request(method, url, params=params, data=data,
                                            headers=headers, timeout=timeout)
        r.raise_for_status()
    except requests.HTTPError as e:
        raise APIStatusError("API returned error code {}".format(e.response.status_code))
    except requests.RequestException as e:
        raise APIRequestError("Error while connecting to API: {}".format(e))

    return r
