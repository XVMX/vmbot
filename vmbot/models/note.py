# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
from datetime import datetime, timedelta
import bisect

from xmpp.protocol import JID

from ..helpers import database as db
from .message import Message, msg_type_enum

QUEUE_UPDATE_INTERVAL = 12 * 60 * 60
QUEUE_MAX_OFFSET = timedelta(hours=14)
NOTE_DELIVERY_FRAME = timedelta(days=30)


class Note(db.Model):
    """Store a note to be sent to a user."""
    __tablename__ = "pager"

    note_id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    receiver = db.Column(db.Text, nullable=False)
    room = db.Column(db.Text)
    data = db.Column(db.Text, nullable=False)
    offset_time = db.Column(db.DateTime, nullable=False)
    message_type = db.Column(msg_type_enum, nullable=False)

    _queue_update = None
    _note_queue = []

    def __init__(self, receiver, message, offset_time, room=None, type_="groupchat"):
        self.receiver = receiver
        self.room = room
        self.data = message
        self.offset_time = offset_time
        self.message_type = type_

    def to_msg(self):
        return Message(self.room or self.receiver, self.data, self.message_type)

    @classmethod
    def process_notes(cls, nick_dict, session):
        if cls._queue_update is None or cls._queue_update <= time.time():
            cls.update_queue(session)

        cur_time = datetime.utcnow()
        JID_ALL = 0
        jids = {}

        ids, picks = [], []
        for idx, (offset, note) in enumerate(cls._note_queue):
            if offset > cur_time:
                break

            id_, recv, room = note
            if room is None:
                # PM
                if JID_ALL not in jids:
                    jids[JID_ALL] = {jid.getStripped() for room in nick_dict.values()
                                     for jid in room.values()}
                if recv in jids[JID_ALL]:
                    ids.append(id_)
                    picks.append(idx)
            else:
                # MUC
                room = JID(room).getNode()
                if room in nick_dict:
                    if room not in jids:
                        jids[room] = {jid.getNode() for jid in nick_dict[room].values()}
                    if recv in nick_dict[room] or recv in jids[room]:
                        ids.append(id_)
                        picks.append(idx)

        if not ids:
            return []

        # picks is sorted because note_queue is sorted
        for idx in reversed(picks):
            del cls._note_queue[idx]

        messages = []
        for note in session.execute(db.select(Note).where(Note.note_id.in_(ids))).scalars():
            messages.append(note.to_msg())
            session.delete(note)

        session.commit()
        return messages

    @classmethod
    def update_queue(cls, session):
        cur_time = datetime.utcnow()
        max_offset = cur_time + QUEUE_MAX_OFFSET
        select_notes = (db.select(Note.note_id, Note.receiver, Note.room, Note.offset_time).
                        where(Note.offset_time <= max_offset).order_by(Note.offset_time.asc()))

        cls._note_queue, expired = [], []
        for note in session.execute(select_notes):
            if cur_time - note[-1] > NOTE_DELIVERY_FRAME:
                expired.append(note[0])
            else:
                cls._note_queue.append((note[-1], note[:-1]))
        # note_queue is sorted because the database results are

        if expired:
            # Session is synchronized after commit
            session.execute(db.delete(Note).where(Note.note_id.in_(expired)).
                            execution_options(synchronize_session=False))
            session.commit()

        cls._queue_update = time.time() + QUEUE_UPDATE_INTERVAL

    @classmethod
    def add_note(cls, note, session):
        session.add(note)
        session.commit()

        # Update note queue
        if note.offset_time <= datetime.utcnow() + QUEUE_MAX_OFFSET:
            bisect.insort(cls._note_queue,
                          (note.offset_time, (note.note_id, note.receiver, note.room)))
