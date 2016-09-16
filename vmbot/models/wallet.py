# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime

from ..helpers import database as db

# See https://api.eveonline.com/eve/RefTypes.xml.aspx
REF_REVENUE = {
    'PvE': (17, 33, 34, 85, 99, 125),  # Bounties, Mission Rewards, Incursions, Project Discovery
    'POCO': (96, 97),  # Planetary Import/Export Tax
    'Reprocessing': (127,),  # Reprocessing Tax
    'Services': (13, 14, 55, 128)  # Office Rental Fee, Factory Slot Rental Fee, Jump Clone Fees
}


class WalletJournalEntry(db.Model):
    """Store a wallet journal entry."""
    __tablename__ = "corp_wallet"

    ref_id = db.Column(db.BigInteger, nullable=False, primary_key=True, autoincrement=False)
    type_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    def __init__(self, ref_id, type_id, amount, date):
        self.ref_id = ref_id
        self.type_id = type_id
        self.amount = amount
        self.date = date

    @classmethod
    def from_xml_row(cls, row):
        row = row.attrib
        ref_id, type_id, amount = int(row['refID']), int(row['refTypeID']), float(row['amount'])
        date = datetime.strptime(row['date'], "%Y-%m-%d %H:%M:%S")

        return cls(ref_id, type_id, amount, date)
