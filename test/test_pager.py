# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from datetime import datetime

from xmpp.protocol import JID, Message

import vmbot.helpers.database as db

from vmbot.pager import Pager


def msg_recvr(mess):
    return mess.getTo().getStripped()


class TestPager(unittest.TestCase):
    db_engine = db.create_engine("sqlite://")
    default_mess = Message(to=JID("sender"), frm=JID("room"))
    default_args = "user 2d5h13m text"

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
        self.pager = Pager()
        self.pager.jid = JID("vmbot@example.com")
        self.pager.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                        side_effect=msg_recvr)
        self.pager.get_sender_username = mock.MagicMock(name="get_sender_username",
                                                        side_effect=msg_recvr)

    def tearDown(self):
        del self.pager

    def test_process_pager_args(self):
        res = self.pager._process_pager_args(self.default_args)

        self.assertEqual(res[0], "user")
        self.assertEqual(res[1], "text")
        self.assertIsInstance(res[2], datetime)

    def test_process_pager_args_quoted(self):
        res = self.pager._process_pager_args('"spaced user" 2d5h13m text')

        self.assertEqual(res[0], "spaced user")
        self.assertEqual(res[1], "text")
        self.assertIsInstance(res[2], datetime)

    def test_process_pager_args_noargs(self):
        self.assertRaises(ValueError, self.pager._process_pager_args, "")
        self.assertRaises(ValueError, self.pager._process_pager_args, "user")

    def test_process_pager_args_notext(self):
        self.assertRaises(ValueError, self.pager._process_pager_args, "user 2d5h13m")

    def test_process_pager_args_invalidoffset(self):
        res = self.pager._process_pager_args("user -13d+8y5h text")

        self.assertEqual(res[0], "user")
        self.assertEqual(res[1], "-13d+8y5h text")
        self.assertIsInstance(res[2], datetime)

    def test_remindme(self):
        self.assertIn("Reminder for sender will be sent at ",
                      self.pager.remindme(self.default_mess, "2d5h13m text"))

    def test_remindme_noargs(self):
        self.assertEqual(self.pager.remindme(self.default_mess, "text"),
                         "Please specify a time offset and a message")

    def test_sendmsg(self):
        self.assertIn("Message for user will be sent at ",
                      self.pager.sendmsg(self.default_mess, self.default_args))

    def test_sendmsg_noargs(self):
        self.assertEqual(self.pager.sendmsg(self.default_mess, "user"),
                         ("Please provide a username, a message to send, "
                          "and optionally a time offset: <user> [offset] <msg>"))

    def test_sendpm(self):
        self.assertIn("PM for user will be sent at ",
                      self.pager.sendpm(self.default_mess, self.default_args))

    def test_sendpm_noargs(self):
        self.assertEqual(self.pager.sendpm(self.default_mess, "user"),
                         ("Please provide a username, a message to send, "
                          "and optionally a time offset: <user> [offset] <msg>"))


if __name__ == "__main__":
    unittest.main()
