# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from datetime import datetime

from xmpp.protocol import JID, Message

import vmbot.helpers.database as db

from vmbot.pager import Pager
from vmbot.helpers.notequeue import NoteQueue


def mock_uname_from_mess(mess, full_jid=False):
    return JID("sender@domain.tld/res") if full_jid else "sender"


class TestPager(unittest.TestCase):
    db_engine = db.create_engine("sqlite://")
    muc_mess = Message(frm=JID("room@conf.domain.tld/sender"), typ=b"groupchat")
    pm_mess = Message(frm=JID("sender@domain.tld/res"), typ=b"chat")
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
        self.pager.jid = JID("bot@domain.tld/res")
        self.pager.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                        side_effect=mock_uname_from_mess)
        self.pager.get_sender_username = mock.MagicMock(name="get_sender_username",
                                                        return_value="sender")
        self.pager.notes = mock.MagicMock(name="notes", spec=NoteQueue)

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

    def test_process_pager_args_requiredoffset(self):
        self.assertRaises(ValueError, self.pager._process_pager_args,
                          "user text", require_offset=True)

    def test_remindme(self):
        self.assertIn("Reminder for sender will be sent at ",
                      self.pager.remindme(self.muc_mess, "2d5h13m text"))

    def test_remindme_pm(self):
        self.assertIn("Reminder for sender@domain.tld will be sent at ",
                      self.pager.remindme(self.pm_mess, "2d5h13m text"))

    def test_remindme_noargs(self):
        self.assertEqual(self.pager.remindme(self.muc_mess, "text"),
                         "Please specify a time offset and a message")

    def test_remindme_nooffset(self):
        self.assertEqual(self.pager.remindme(self.muc_mess, "text text2"),
                         "Please provide a non-zero time offset")

    def test_sendmsg(self):
        self.assertIn("Message for user will be sent at ",
                      self.pager.sendmsg(self.muc_mess, self.default_args))

    def test_sendmsg_jid(self):
        self.assertIn("Message for user will be sent at ",
                      self.pager.sendmsg(self.muc_mess, "user@domain.tld 2d5h13m text"))

    def test_sendmsg_pm(self):
        self.assertIsNone(self.pager.sendmsg(self.pm_mess, self.default_args))

    def test_sendmsg_noargs(self):
        self.assertEqual(self.pager.sendmsg(self.muc_mess, "user"),
                         ("Please provide a username, a message to send, "
                          "and optionally a time offset: <user> [offset] <msg>"))

    def test_sendpm(self):
        self.assertIn("PM for user@domain.tld will be sent at ",
                      self.pager.sendpm(self.muc_mess, self.default_args))

    def test_sendpm_jid(self):
        self.assertIn("PM for user@domain.tld will be sent at ",
                      self.pager.sendpm(self.muc_mess, "user@domain.tld 2d5h13m text"))

    def test_sendpm_noargs(self):
        self.assertEqual(self.pager.sendpm(self.muc_mess, "user"),
                         ("Please provide a username, a message to send, "
                          "and optionally a time offset: <user> [offset] <msg>"))


if __name__ == "__main__":
    unittest.main()
