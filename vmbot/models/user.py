# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime

from ..helpers import database as db


class User(db.Model):
    """Store data about a user."""
    __tablename__ = "users"

    jid = db.Column(db.String, nullable=False, primary_key=True)
    allow_director = db.Column(db.Boolean, default=False, nullable=False)
    allow_admin = db.Column(db.Boolean, default=False, nullable=False)
    nicks = db.relationship("Nickname", back_populates="user", cascade="all, delete-orphan",
                            lazy=False, order_by="Nickname.last_seen.desc()", uselist=True)

    def __init__(self, jid):
        self.jid = jid

    @property
    def uname(self):
        return self.jid.split('@', 1)[0]

    @property
    def last_seen(self):
        # self.nicks is ordered by last_seen (descending)
        return self.nicks[0].last_seen if self.nicks else None


class Nickname(db.Model):
    """Store a nickname belonging to a user."""
    __tablename__ = "nicknames"

    nick = db.Column(db.String, nullable=False, primary_key=True)
    _user_jid = db.Column("user_jid", db.String, db.ForeignKey("users.jid"),
                          nullable=False, primary_key=True)
    last_seen = db.Column(db.DateTime, nullable=False)
    user = db.relationship("User", back_populates="nicks", lazy=True, uselist=False)

    def __init__(self, nick):
        self.nick = nick
        self.last_seen = datetime.utcnow()
