# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime, timedelta
import os

from xmpp.protocol import JID

from vmbot.helpers.files import BOT_DB
import vmbot.helpers.database as db

from vmbot.models.note import Note, NOTE_DELIVERY_FRAME

CUR_TIME = datetime.utcnow()
FUT_TIME = datetime.utcnow() + timedelta(hours=3)
EXP_TIME = datetime.utcnow() - (NOTE_DELIVERY_FRAME + timedelta(days=5))
NOTES = [
    ["receiver1@example.com", "PM text", CUR_TIME, None, "chat"],
    ["receiver2@example.com", "Future text", FUT_TIME, None, "chat"],
    ["receiver3@example.com", "Expired text", EXP_TIME, None, "chat"],
    ["user4", "MUC text", CUR_TIME, "room1@example.com"],
    ["user5", "Missing MUC text", CUR_TIME, "room2@example.com"]
]
NICK_DICT = {
    'room1': {
        'user1': JID("receiver1@example.com"),
        'user2': JID("receiver2@example.com"),
        'user4': JID("receiver4@example.com"),
        'user5': JID("receiver5@example.com")
    }
}


class TestNote(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            os.remove(BOT_DB)
        except OSError:
            pass
        else:
            db.init_db()

    @classmethod
    def tearDownClass(cls):
        return cls.setUpClass()

    def setUp(self):
        self.sess = db.Session()
        self.notes = [Note(*args) for args in NOTES]

    def tearDown(self):
        del self.notes
        self.sess.close()

    def test_to_msg(self):
        msg = self.notes[0].to_msg()
        self.assertEqual(msg.receiver, NOTES[0][0])
        self.assertEqual(msg.data, NOTES[0][1])
        self.assertEqual(msg.message_type, NOTES[0][4])

    def test_add_note(self):
        for note in self.notes:
            Note.add_note(note)
            self.assertIsNotNone(note.note_id)

        for note in ((note.offset_time, (note.note_id, note.receiver, note.room))
                     for note in self.notes):
            self.assertIn(note, Note._note_queue)

        # Clean up database and class
        for note in self.notes:
            self.sess.delete(note)
        self.sess.commit()

        Note._queue_update = None
        Note._note_queue.clear()

    def test_queue(self):
        for note in self.notes:
            Note.add_note(note, self.sess)

        res = Note.process_notes(NICK_DICT, self.sess)
        self.assertEqual(len(res), 2)

        valid_rcvr = [self.notes[0].receiver, self.notes[3].room]
        valid_data = [self.notes[0].data, self.notes[3].data]
        for msg in res:
            self.assertIn(msg.receiver, valid_rcvr)
            self.assertIn(msg.data, valid_data)

        # All notes have been processed already
        self.assertEqual(Note.process_notes(NICK_DICT, self.sess), [])


if __name__ == "__main__":
    unittest.main()