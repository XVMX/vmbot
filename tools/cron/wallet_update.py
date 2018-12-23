# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.models import WalletJournalEntry

import config

WALLET_UPDATE_INTERVAL = 30 * 60
WALLET_DIVISION = 1


def init(session, token):
    if "esi-wallet.read_corporation_wallets.v1" not in token.scopes:
        print('SSO token is missing "esi-wallet.read_corporation_wallets.v1" scope')
        return

    return main(session, token)


def needs_run(session):
    return Storage.get(session, "wallet_update_next_run") <= time.time()


def main(session, token):
    Storage.set(session, "wallet_update_next_run", time.time() + WALLET_UPDATE_INTERVAL)
    walk_journal(session, token)


def walk_journal(session, token):
    known_ids = {res[0] for res in session.query(WalletJournalEntry.ref_id).all()}

    entries, pages = get_entries(token)
    raw_len = len(entries)
    entries = filter_known_entries(known_ids, entries)
    session.add_all(entries)
    session.commit()

    for p in range(2, pages + 1):
        if len(entries) != raw_len:
            break

        entries = get_entries(token, page=p)
        raw_len = len(entries)
        entries = filter_known_entries(known_ids, entries)
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
        return ([WalletJournalEntry.from_esi_record(rec) for rec in recs],
                int(head.get('X-Pages', 1)))

    return [WalletJournalEntry.from_esi_record(rec) for rec in recs]


def filter_known_entries(known_ids, entries):
    new_entries = []

    for entry in entries:
        if entry.ref_id not in known_ids:
            known_ids.add(entry.ref_id)
            new_entries.append(entry)

    return new_entries
