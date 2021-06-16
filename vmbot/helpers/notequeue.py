# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
from datetime import datetime, timedelta
import bisect

from xmpp.protocol import JID

from . import database as db
from ..models import Note

QUEUE_UPDATE_INTERVAL = 12 * 60 * 60
QUEUE_MAX_OFFSET = timedelta(hours=14)
NOTE_DELIVERY_FRAME = timedelta(days=30)


class NoteQueue(object):
    """Store upcoming notes in memory until they are delivered."""

    def __init__(self):
        self._next_update = time.time()
        self._queue = []

    def fetch(self, nick_dict, session):
        """Retrieve due notes from the queue if their receivers are online."""
        if self._next_update <= time.time():
            self.update_queue(session)

        cur_time = datetime.utcnow()
        JID_ALL = 0
        jids = {}

        ids, picks = [], []
        for idx, (offset, note) in enumerate(self._queue):
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
            del self._queue[idx]

        messages = []
        for note in session.execute(db.select(Note).where(Note.note_id.in_(ids))).scalars():
            messages.append(note.to_msg())
            session.delete(note)

        session.commit()
        return messages

    def update_queue(self, session):
        cur_time = datetime.utcnow()
        select_notes = (db.select(Note.note_id, Note.receiver, Note.room, Note.offset_time).
                        where(Note.offset_time <= cur_time + QUEUE_MAX_OFFSET).
                        order_by(Note.offset_time.asc()))

        self._queue, expired = [], []
        for note in session.execute(select_notes):
            if cur_time - note[-1] > NOTE_DELIVERY_FRAME:
                expired.append(note[0])
            else:
                self._queue.append((note[-1], note[:-1]))
        # note_queue is sorted because the database results are

        if expired:
            # Session is synchronized after commit
            session.execute(db.delete(Note).where(Note.note_id.in_(expired)).
                            execution_options(synchronize_session=False))
            session.commit()

        self._next_update = time.time() + QUEUE_UPDATE_INTERVAL

    def add_note(self, note, session):
        session.add(note)
        session.commit()

        # Update note queue, keeping it sorted
        if note.offset_time <= datetime.utcnow() + QUEUE_MAX_OFFSET:
            bisect.insort(self._queue,
                          (note.offset_time, (note.note_id, note.receiver, note.room)))
