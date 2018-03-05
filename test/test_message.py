# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from vmbot.models.message import Message


class TestMessage(unittest.TestCase):
    def setUp(self):
        self.mess = Message("receiver", "text", "chat")

    def tearDown(self):
        del self.mess

    def test_send_dict(self):
        self.assertDictEqual(self.mess.send_dict,
                             {'user': "receiver", 'text': "text", 'message_type': "chat"})


if __name__ == "__main__":
    unittest.main()
