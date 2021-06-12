# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime, timedelta

from xmpp.protocol import JID

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
        'user1': JID("receiver1@example.com/res1"),
        'user2': JID("receiver2@example.com/res2"),
        'user4': JID("receiver4@example.com/res4"),
        'user5': JID("receiver5@example.com/res5")
    }
}


class TestNote(unittest.TestCase):
    db_engine = db.create_engine("sqlite://")

    @classmethod
    def setUpClass(cls):
        db.init_db(cls.db_engine)
        db.Session.configure(bind=cls.db_engine)

    @classmethod
    def tearDownClass(cls):
        db.Session.configure(bind=db.engine)
        cls.db_engine.dispose()
        del cls.db_engine

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
            Note.add_note(note, self.sess)
            self.assertIsNotNone(note.note_id)

        for note in self.notes:
            self.assertIn((note.offset_time, (note.note_id, note.receiver, note.room)),
                          Note._note_queue)

        # Clean up database and class
        for note in self.notes:
            self.sess.delete(note)
        self.sess.commit()

        Note._queue_update = None
        Note._note_queue = []

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
