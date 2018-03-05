# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from ..helpers import database as db


class Message(db.Model):
    """Store a message to be sent to a Jabber entity upon retrieval."""
    __tablename__ = "messages"

    message_id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    receiver = db.Column(db.String, nullable=False)
    data = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.Enum("chat", "groupchat"), nullable=False)

    def __init__(self, receiver, message, type_="groupchat"):
        self.receiver = receiver
        self.data = message
        self.message_type = type_

    @property
    def send_dict(self):
        """Message in JabberBot.send format."""
        return {'user': self.receiver, 'text': self.data, 'message_type': self.message_type}
