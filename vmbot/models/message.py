# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from ..helpers import database as db

msg_type_enum = db.Enum("chat", "groupchat", name="message_type")


class Message(db.Model):
    """Store a message to be sent to a Jabber entity upon retrieval."""
    __tablename__ = "messages"

    message_id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    receiver = db.Column(db.Text, nullable=False)
    data = db.Column(db.Text, nullable=False)
    message_type = db.Column(msg_type_enum, nullable=False)

    def __init__(self, receiver, message, type_="groupchat"):
        self.receiver = receiver
        self.data = message
        self.message_type = type_

    @property
    def send_dict(self):
        """Message in JabberBot.send format."""
        return {'user': self.receiver, 'text': self.data, 'message_type': self.message_type}
