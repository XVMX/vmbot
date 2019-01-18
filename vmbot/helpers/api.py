# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime
import threading
import logging
import traceback

from ..jabberbot import __version__ as jb_version
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

from .files import HTTPCACHE
from .exceptions import APIError, APIStatusError, APIRequestError
from .time import ISO8601_DATETIME_FMT
from . import staticdata
from .format import format_tickers
from ..models import ISK

import config

_API_REG = threading.local()


def _get_requests_session():
    """Retrieve or create a thread-local requests session."""
    try:
        return _API_REG.http_sess
    except AttributeError:
        sess = requests.session()
        ua = "XVMX VMBot (JabberBot {}) ".format(jb_version) + sess.headers['User-Agent']
        sess.headers['User-Agent'] = ua

        _API_REG.http_sess = CacheControl(sess, cache=FileCache(HTTPCACHE))
        return _API_REG.http_sess


def get_names(*ids):
    """Resolve char_ids/corp_ids/ally_ids to their names."""
    try:
        res = request_esi("/v2/universe/names/", json=ids, method="POST")
    except APIError:
        return {id_: "{ERROR}" for id_ in ids}

    # ESI returns either names for all ids or none at all
    # See https://esi.evetech.net/ui/#/operations/Universe/post_universe_names
    return {item['id']: item['name'] for item in res}


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
        zkb = request_api(url).json()
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
    name = get_names(victim.get('character_id', victim['corporation_id'])).values()[0]
    system = staticdata.system_data(killdata['solar_system_id'])
    corp_ticker, alliance_ticker = get_tickers(victim['corporation_id'],
                                               victim.get('alliance_id', None))
    killtime = datetime.strptime(killdata['killmail_time'], ISO8601_DATETIME_FMT)

    return ("{} {} | {} ({:,} point(s)) | {:.2f} ISK | "
            "{} ({}) | {} participant(s) ({:,} damage) | {:%Y-%m-%d %H:%M:%S}").format(
        name, format_tickers(corp_ticker, alliance_ticker),
        staticdata.type_name(victim['ship_type_id']), zkb['points'],
        ISK(zkb['totalValue']), system['system_name'], system['region_name'],
        len(killdata['attackers']), victim['damage_taken'], killtime
    )


def request_esi(route, fmt=(), params=None, data=None, headers=None,
                timeout=3, json=None, method="GET", with_head=False):
    url = route.format(*fmt)
    if url.startswith('/'):
        url = config.ESI['base_url'] + url

    full_params = {'datasource': config.ESI['datasource'], 'language': config.ESI['lang']}
    if params is not None:
        full_params.update(params)

    r = request_api(url, params=full_params, data=data, headers=headers,
                    timeout=timeout, json=json, method=method)

    if not r.from_cache and 'warning' in r.headers:
        # Versioned endpoint is outdated (199) or deprecated (299)
        kw = "outdated" if r.headers['warning'][:3] == "199" else "deprecated"
        # Omit top stack frame (this function) and strip trailing newline
        trace = "".join(traceback.format_stack(limit=3)[:-1])[:-1]

        warn = 'Route "{}" is {}'.format(route, kw)
        warn += "\nResponse header: warning: " + r.headers['warning']
        warn += "\nTraceback (most recent call last):\n```\n" + trace + "\n```"
        logging.getLogger(__name__ + ".esi").warning(warn, extra={'gh_labels': ["esi-warning"]})

    if with_head:
        return r.json(), r.headers
    return r.json()


def request_api(url, params=None, data=None, headers=None,
                auth=None, timeout=3, json=None, method="GET"):
    try:
        r = _get_requests_session().request(method, url, params=params, data=data,
                                            headers=headers, auth=auth, timeout=timeout, json=json)
        r.raise_for_status()
    except requests.HTTPError as e:
        raise APIStatusError(e, "API returned error code {}".format(e.response.status_code))
    except requests.RequestException as e:
        raise APIRequestError(e, "Error while connecting to API: {}".format(e))

    return r
