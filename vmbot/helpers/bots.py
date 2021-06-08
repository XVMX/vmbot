# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime

from .exceptions import APIError, APIStatusError
from .time import ISO8601_DATETIME_FMT, parse_iso8601_duration
from . import api
from . import staticdata
from .format import format_tickers
from ..models import ISK

import config


def zbot(kill_id):
    """Create a compact overview of a zKB killmail."""
    try:
        zkb = api.request_api("https://zkillboard.com/api/killID/{}/".format(kill_id)).json()
    except APIError as e:
        return unicode(e)

    if not zkb:
        return "Failed to load data for https://zkillboard.com/kill/{}/".format(kill_id)

    zkb = zkb[0]['zkb']
    try:
        killdata = api.request_esi("/v1/killmails/{}/{}/", (kill_id, zkb['hash']))
    except APIError as e:
        return unicode(e)

    victim = killdata['victim']
    name = api.get_names(victim.get('character_id', victim['corporation_id'])).values()[0]
    system = staticdata.system_data(killdata['solar_system_id'])
    corp_ticker, alliance_ticker = api.get_tickers(victim['corporation_id'],
                                                   victim.get('alliance_id', None))
    killtime = datetime.strptime(killdata['killmail_time'], ISO8601_DATETIME_FMT)

    return ("{} {} | {} ({:,} point(s)) | {:.2f} ISK | "
            "{} ({}) | {:,} attacker(s) ({:,} damage) | {:%Y-%m-%d %H:%M:%S}").format(
        name, format_tickers(corp_ticker, alliance_ticker),
        staticdata.type_name(victim['ship_type_id']), zkb['points'],
        ISK(zkb['totalValue']), system['system_name'], system['region_name'],
        len(killdata['attackers']), victim['damage_taken'], killtime
    )


def ytbot(video_id):
    """Create a compact overview of a YouTube video."""
    if not config.YT_KEY:
        return False

    fields = ("items(snippet(publishedAt,channelTitle,liveBroadcastContent,localized/title),"
              "contentDetails(duration,definition),statistics(viewCount,likeCount,dislikeCount))")
    params = {'part': "snippet,contentDetails,statistics", 'id': video_id,
              'hl': "en", 'fields': fields, 'key': config.YT_KEY, 'prettyPrint': "false"}
    try:
        yt = api.request_api("https://www.googleapis.com/youtube/v3/videos", params=params).json()
    except APIStatusError as e:
        res = e.response.json()
        if e.status_code == 403:
            if any(err['reason'] == "quotaExceeded" for err in res['error']['errors']):
                return False
        elif e.status_code == 404:
            return None
        return unicode(e) + ": " + res['error']['message']
    except APIError as e:
        return unicode(e)

    if not yt['items']:
        return None
    yt = yt['items'][0]

    res = yt['snippet']['localized']['title']
    bcast = yt['snippet']['liveBroadcastContent']
    dur = parse_iso8601_duration(yt['contentDetails']['duration'])
    if bcast == "live":
        res += " | LIVE"
    elif bcast == "upcoming":
        res += " | Upcoming"
    if yt['contentDetails']['definition'] == "hd":
        res += " | HD"
    res += " | " + yt['snippet']['channelTitle']
    if dur:
        res += " | {}".format(dur)

    stats = yt['statistics']
    views = int(stats['viewCount'])
    res += " | {:,} views".format(views)
    if 'likeCount' in stats and 'dislikeCount' in stats:
        likes, dislikes = int(stats['likeCount']), int(stats['dislikeCount'])
        perc_like = likes / float(likes + dislikes)
        res += " | {:.2%} likes (+{:,}/-{:,})".format(perc_like, likes, dislikes)

    published = datetime.strptime(yt['snippet']['publishedAt'], ISO8601_DATETIME_FMT)
    res += " | {:%Y-%m-%d %H:%M:%S}".format(published)

    return res
