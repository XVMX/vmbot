# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.helpers import api
from vmbot.helpers import staticdata
from vmbot.helpers.format import format_tickers
from vmbot.models.messages import Message
from vmbot.models import ISK

import config

KM_MIN_VAL = 5000000
REDISQ_URL = "https://redisq.zkillboard.com/listen.php"
FEED_FMT = "\n{} {} | {} | {:.2f} ISK | {} ({}) | {} | https://zkillboard.com/kill/{}/"


def init(session):
    Storage.set(session, "km_feed_next_run", time.time())


def needs_run(session):
    return Storage.get(session, "km_feed_next_run") <= time.time()


def main(session):
    Storage.set(session, "km_feed_next_run", time.time() + 10 * 60)

    losses = []
    while True:
        try:
            res = api.request_rest(REDISQ_URL, params={'ttw': 3}, timeout=5)['package']
        except APIError:
            break

        if res is None:
            break
        if (res['killmail']['victim']['corporation']['id'] == config.CORPORATION_ID
                and res['zkb']['totalValue'] >= KM_MIN_VAL):
            losses.append(res)

    if not losses:
        return

    reply = "{} new loss(es):".format(len(losses))
    for loss in losses:
        km, zkb = loss['killmail'], loss['zkb']
        victim = km['victim']
        system = staticdata.solarSystemData(km['solarSystem']['id'])
        corp_ticker, alliance_ticker = api.get_tickers(
            victim['corporation']['id'],
            victim['alliance']['id'] if 'alliance' in victim else None
        )

        reply += FEED_FMT.format(
            victim['character']['name'] if 'character' in victim else victim['corporation']['name'],
            format_tickers(corp_ticker, alliance_ticker),
            victim['shipType']['name'], ISK(zkb['totalValue']),
            system['solarSystemName'], system['regionName'],
            km['killTime'], km['killID']
        )

    for room in config.JABBER['primary_chatrooms']:
        session.add(Message(room, reply, "groupchat"))
    session.commit()
