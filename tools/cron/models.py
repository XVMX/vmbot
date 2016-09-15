# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from . import path

import vmbot.helpers.database as db


class Storage(db.Model):
    """Store arbitrary Python objects persistently."""
    __tablename__ = "cron_storage"

    key = db.Column(db.String, nullable=False, primary_key=True)
    value = db.Column(db.PickleType, nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    @classmethod
    def get(cls, session, key):
        """Return value stored at key."""
        res = session.query(cls.value).filter_by(key=key).scalar()
        if res is None:
            raise KeyError

        return res

    @classmethod
    def set(cls, session, key, value):
        """Set key to store value."""
        session.merge(cls(key, value))
        session.commit()

    @classmethod
    def delete(cls, session, key):
        """Delete value stored at key."""
        session.query(cls).filter_by(key=key).delete()
        session.commit()
