# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime

from ..helpers.time import ISO8601_DATETIME_FMT
from ..helpers import database as db


class WalletJournalEntry(db.Model):
    """Store a wallet journal entry."""
    __tablename__ = "corp_wallet"

    ref_id = db.Column(db.BigInteger, nullable=False, primary_key=True, autoincrement=False)
    ref_type = db.Column(db.Text, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    def __init__(self, ref_id, ref_type, amount, date):
        self.ref_id = ref_id
        self.ref_type = ref_type
        self.amount = amount
        self.date = date

    @classmethod
    def from_esi_record(cls, record):
        date = datetime.strptime(record['date'], ISO8601_DATETIME_FMT)
        return cls(record['id'], record['ref_type'], record.get('amount', 0.0), date)
