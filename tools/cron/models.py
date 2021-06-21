# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import json

from sqlalchemy.ext.hybrid import hybrid_property

from . import path

import vmbot.helpers.database as db

JSON_SEPS = (',', ':')


class Storage(db.Model):
    """Store JSON-compatible Python objects persistently."""
    __tablename__ = "cron_storage"

    key = db.Column(db.Text, nullable=False, primary_key=True)
    _value = db.Column("value", db.Text, nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    @hybrid_property
    def value(self):
        return json.loads(self._value)

    @value.setter
    def value(self, value):
        self._value = json.dumps(value, separators=JSON_SEPS)

    @value.expression
    def value(self):
        return self._value

    @classmethod
    def get(cls, session, key):
        """Return value stored at key."""
        res = session.get(cls, key)
        if res is None:
            raise KeyError

        return res.value

    @classmethod
    def set(cls, session, key, value):
        """Set key to store value."""
        session.merge(cls(key, value))
        session.commit()

    @classmethod
    def delete(cls, session, key):
        """Delete value stored at key."""
        res = session.get(cls, key)
        if res is not None:
            session.delete(res)
            session.commit()
