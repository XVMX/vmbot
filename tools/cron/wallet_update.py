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

    entries = filter_known_entries(known_ids, get_entries(token))
    session.add_all(entries)
    session.commit()

    # ESI returns up to 500 journal entries at once
    while len(entries) == 500:
        min_id = min(entry.ref_id for entry in entries)
        entries = filter_known_entries(known_ids, get_entries(token, from_id=min_id))
        session.add_all(entries)
        session.commit()


def get_entries(token, from_id=None):
    if "esi-wallet.read_corporation_wallets.v1" not in token.scopes:
        return []

    params = {'from_id': from_id}
    try:
        recs = token.request_esi("/v2/corporations/{}/wallets/{}/journal/",
                                 (config.CORPORATION_ID, WALLET_DIVISION), params=params)
    except APIError:
        return []

    return [WalletJournalEntry.from_esi_record(rec) for rec in recs]


def filter_known_entries(known_ids, entries):
    new_entries = []

    for entry in entries:
        if entry.ref_id not in known_ids:
            known_ids.add(entry.ref_id)
            new_entries.append(entry)

    return new_entries
