# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime

from vmbot.models.note import Note


class TestNote(unittest.TestCase):
    def setUp(self):
        self.note = Note("receiver", "text", datetime.utcnow(), type_="chat")

    def tearDown(self):
        del self.note

    def test_to_msg(self):
        msg = self.note.to_msg()
        self.assertEqual(msg.receiver, "receiver")
        self.assertEqual(msg.data, "text")
        self.assertEqual(msg.message_type, "chat")


if __name__ == "__main__":
    unittest.main()
