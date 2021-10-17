# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime

from ..helpers import database as db


class MarketStructure(db.Model):
    """Store information on a suspected market structure."""
    __tablename__ = "market_structures"

    structure_id = db.Column(db.BigInteger, nullable=False, primary_key=True, autoincrement=False)
    type_id = db.Column(db.Integer, index=True)
    system_id = db.Column(db.Integer)
    has_market = db.Column(db.Boolean, nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False, onupdate=datetime.utcnow)

    def __init__(self, structure_id, type_id, system_id):
        self.structure_id = structure_id
        self.type_id = type_id
        self.system_id = system_id
        self.has_market = True  # optimistic default
        self.last_updated = datetime.utcnow()

    @classmethod
    def from_esi_result(cls, structure_id, result):
        return cls(structure_id, result.get("type_id", None), result["solar_system_id"])

    @classmethod
    def from_esi_denied(cls, structure_id):
        res = cls(structure_id, None, None)
        res.has_market = False  # access denied
        return res

    @property
    def update_age(self):
        return datetime.utcnow() - self.last_updated
