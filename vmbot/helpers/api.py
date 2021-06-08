# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import threading
import logging
import traceback

from ..jabberbot import __version__ as jb_version
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

from .files import HTTPCACHE
from .exceptions import APIError, APIStatusError, APIRequestError

import config

_API_REG = threading.local()


def _get_requests_session():
    """Retrieve or create a thread-local requests session."""
    try:
        return _API_REG.http_sess
    except AttributeError:
        sess = requests.session()
        ua = "XVMX-VMBot (JabberBot {}) ".format(jb_version) + sess.headers['User-Agent']
        sess.headers['User-Agent'] = ua

        _API_REG.http_sess = CacheControl(sess, cache=FileCache(HTTPCACHE))
        return _API_REG.http_sess


def get_names(*ids):
    """Resolve char_ids/corp_ids/ally_ids to their names."""
    try:
        res = request_esi("/v3/universe/names/", json=ids, method="POST")
    except APIError:
        return {id_: "{ERROR}" for id_ in ids}

    # ESI returns either names for all ids or none at all
    # See https://esi.evetech.net/ui/#/Universe/post_universe_names
    return {item['id']: item['name'] for item in res}


def get_tickers(corp_id, ally_id):
    """Resolve corp_id/ally_id to their respective ticker(s)."""
    corp_ticker = None
    if corp_id:
        corp_ticker = "ERROR"
        try:
            corp = request_esi("/v5/corporations/{}/", (corp_id,))
        except APIError:
            pass
        else:
            corp_ticker = corp['ticker']
            ally_id = ally_id or corp.get('alliance_id', None)

    alliance_ticker = None
    if ally_id:
        alliance_ticker = "ERROR"
        try:
            ally = request_esi("/v4/alliances/{}/", (ally_id,))
        except APIError:
            pass
        else:
            alliance_ticker = ally['ticker']

    return corp_ticker, alliance_ticker


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
