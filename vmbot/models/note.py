# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from ..helpers import database as db
from .message import Message, msg_type_enum


class Note(db.Model):
    """Store a note to be sent to a user."""
    __tablename__ = "pager"

    note_id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    receiver = db.Column(db.Text, nullable=False)
    room = db.Column(db.Text)
    data = db.Column(db.Text, nullable=False)
    offset_time = db.Column(db.DateTime, nullable=False)
    message_type = db.Column(msg_type_enum, nullable=False)

    def __init__(self, receiver, message, offset_time, room=None, type_="groupchat"):
        self.receiver = receiver
        self.room = room
        self.data = message
        self.offset_time = offset_time
        self.message_type = type_

    def to_msg(self):
        return Message(self.room or self.receiver, self.data, self.message_type)
