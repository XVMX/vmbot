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
BASE_URL = "https://zkillboard.com/api/losses/corporationID/{}/no-items/no-attackers/"
INIT_URL = BASE_URL + "limit/1/"
FEED_URL = BASE_URL + "afterKillID/{}/"
FEED_FMT = "\n{} {} | {} | {:.2f} ISK | {} ({}) | {} | https://zkillboard.com/kill/{}/"


def init(session):
    url = INIT_URL.format(config.CORPORATION_ID)
    try:
        res = api.request_rest(url)
    except APIError as e:
        print(unicode(e))
        return

    # res is empty if corporation didn't loose any ships yet
    killID = res[0]['killID'] if res else 0
    Storage.set(session, "km_feed_id", killID)
    Storage.set(session, "km_feed_next_run", time.time())


def main(session):
    if Storage.get(session, "km_feed_next_run") > time.time():
        return
    Storage.set(session, "km_feed_next_run", time.time() + 10 * 60)

    url = FEED_URL.format(config.CORPORATION_ID, Storage.get(session, "km_feed_id"))
    try:
        res = api.request_rest(url)
    except APIError:
        return

    losses = [km for km in res if km['zkb']['totalValue'] >= KM_MIN_VAL]
    if not losses:
        return

    reply = "{} new loss(es):".format(len(losses))
    for loss in reversed(losses):
        victim = loss['victim']
        system = staticdata.solarSystemData(loss['solarSystemID'])
        corp_ticker, alliance_ticker = api.get_tickers(victim['corporationID'],
                                                       victim['allianceID'])

        reply += FEED_FMT.format(
            victim['characterName'] or victim['corporationName'],
            format_tickers(corp_ticker, alliance_ticker),
            staticdata.typeName(victim['shipTypeID']),
            ISK(loss['zkb']['totalValue']),
            system['solarSystemName'], system['regionName'],
            loss['killTime'], loss['killID']
        )

    for room in config.JABBER['primary_chatrooms']:
        session.add(Message(room, reply, "groupchat"))
    session.commit()

    if res:
        Storage.set(session, "km_feed_id", res[0]['killID'])
