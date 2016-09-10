# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import json
import xml.etree.ElementTree as ET

import requests

from .exceptions import APIError, NoCacheError
from . import database as db
from ..models.cache import parse_cache_control, parse_xml_cache, HTTPCacheObject


def get_tickers(corporationID, allianceID):
    """Resolve corpID/allianceID to their respective ticker(s)."""
    corp_ticker = None
    if corporationID:
        corp_ticker = "ERROR"
        try:
            xml = post_xml_endpoint(
                "https://api.eveonline.com/corp/CorporationSheet.xml.aspx",
                params={'corporationID': corporationID}
            )

            corp_ticker = xml.find("ticker").text
            allianceID = allianceID or int(xml.find("allianceID").text) or None
        except (APIError, AttributeError):
            pass

    alliance_ticker = None
    if allianceID:
        alliance_ticker = "ERROR"
        try:
            alliance_ticker = post_xml_endpoint(
                "https://api.eveonline.com/eve/AllianceList.xml.aspx",
                params={'version': 1}
            ).find("rowset/row[@allianceID='{}']".format(allianceID)).attrib['shortName']
        except (APIError, AttributeError):
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

    session.close()
    return json.loads(res.decode("utf-8"))


def post_xml_endpoint(url, params=None, timeout=3):
    session = db.Session()
    res = HTTPCacheObject.get(url, session, params=params)

    if res is None:
        r = request_api(url, params, timeout, method="POST")
        res = ET.fromstring(r.content)

        try:
            expiry = parse_xml_cache(res)
        except NoCacheError:
            pass
        else:
            HTTPCacheObject(url, r.content, expiry, params=params).save(session)
    else:
        res = ET.fromstring(res)

    session.close()
    return res.find("result")


def request_api(url, params=None, timeout=3, method="GET"):
    headers = {'User-Agent': "XVMX JabberBot"}

    try:
        if method in ("GET", "HEAD"):
            r = requests.request(method, url, params=params, headers=headers, timeout=timeout)
        else:
            r = requests.request(method, url, data=params, headers=headers, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise APIError("Error while connecting to EVE-API: {}".format(e))
    if r.status_code != 200:
        raise APIError("EVE-API returned error code {}".format(r.status_code))

    return r
