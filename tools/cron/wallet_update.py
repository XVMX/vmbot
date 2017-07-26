# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.models import WalletJournalEntry

WALLET_JOURNAL_URL = "https://api.eveonline.com/corp/WalletJournal.xml.aspx"
ACCOUNT_KEY = 1000


def init(session, token):
    return main(session, token)


def needs_run(session):
    return Storage.get(session, "wallet_update_next_run") <= time.time()


def main(session, token):
    Storage.set(session, "wallet_update_next_run", time.time() + 30 * 60)
    walk_journal(session, token)


def filter_known_entries(session, entries):
    known_ids = [res[0] for res in session.query(WalletJournalEntry.ref_id).all()]
    new_entries = []

    for entry in entries:
        if entry.ref_id not in known_ids:
            known_ids.append(entry.ref_id)
            new_entries.append(entry)

    return new_entries


def walk_journal(session, token):
    entries = filter_known_entries(session, get_entries(token))
    session.add_all(entries)
    session.commit()

    while len(entries) == 2560:
        min_id = min(entries, key=lambda x: x.ref_id).ref_id
        entries = filter_known_entries(session, get_entries(token, from_id=min_id))
        session.add_all(entries)
        session.commit()


def get_entries(token, from_id=None, limit=2560):
    if "corporationWalletRead" not in token.scopes:
        return []

    params = {'accessType': "corporation", 'accountKey': ACCOUNT_KEY, 'rowCount': limit}
    if from_id:
        params['fromID'] = from_id
    try:
        xml = token.request_xml(WALLET_JOURNAL_URL, params=params)
    except APIError:
        return []

    return [WalletJournalEntry.from_xml_row(row) for row in xml.findall("rowset/row")]
