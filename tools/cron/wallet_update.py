# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.helpers import database as db
from vmbot.models import WalletJournalEntry

import config

# Wallet journal route is cached for up to 1h
WALLET_UPDATE_INTERVAL = 60 * 60
WALLET_DIVISION = 1


def init(session, token):
    if not config.REVENUE_TRACKING:
        return

    if "esi-wallet.read_corporation_wallets.v1" not in token.scopes:
        print('SSO token is missing "esi-wallet.read_corporation_wallets.v1" scope')
        return

    return main(session, token)


def needs_run(session):
    return config.REVENUE_TRACKING and Storage.get(session, "wallet_update_next_run") <= time.time()


def main(session, token):
    Storage.set(session, "wallet_update_next_run", time.time() + WALLET_UPDATE_INTERVAL)
    walk_journal(session, token)


def walk_journal(session, token):
    min_id = session.execute(db.select(db.func.max(WalletJournalEntry.ref_id))).scalar()

    entries, pages = get_entries(token)
    raw_len = len(entries)
    entries = filter_known_entries(min_id, entries)
    session.add_all(entries)
    session.commit()

    for p in range(2, pages + 1):
        if len(entries) != raw_len:
            break

        entries = get_entries(token, page=p)
        raw_len = len(entries)
        entries = filter_known_entries(min_id, entries)
        session.add_all(entries)
        session.commit()


def get_entries(token, page=None):
    if "esi-wallet.read_corporation_wallets.v1" not in token.scopes:
        return ([], 1) if page is None else []

    try:
        recs = token.request_esi("/v4/corporations/{}/wallets/{}/journal/",
                                 (config.CORPORATION_ID, WALLET_DIVISION),
                                 params={'page': page or 1}, with_head=page is None)
    except APIError:
        return ([], 1) if page is None else []

    if page is None:
        recs, head = recs
        return list(map(WalletJournalEntry.from_esi_record, recs)), int(head.get('X-Pages', 1))

    return list(map(WalletJournalEntry.from_esi_record, recs))


def filter_known_entries(min_id, entries):
    if min_id is None:
        return entries

    # Binary search for min_id (entries is sorted in descending order)
    lo, hi = 0, len(entries)
    while lo < hi:
        mid = (lo + hi) // 2
        if entries[mid].ref_id > min_id:
            lo = mid + 1
        else:
            hi = mid

    return entries[:lo]
