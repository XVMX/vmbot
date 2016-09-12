# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from vmbot.helpers.decorators import requires_dir, requires_admin, requires_dir_chat


@requires_dir_chat
@requires_dir
def dir_acl(self, mess, args):
    return True


@requires_admin
def admin_acl(self, mess, args):
    return True


class Message(object):
    def __init__(self, val):
        self.val = val

    def getFrom(self):
        return self

    def getStripped(self):
        return self.val


@mock.patch("config.DIRECTORS", ("Dir1",))
@mock.patch("config.ADMINS", ("Admin1",))
@mock.patch.dict("config.JABBER", {'director_chatrooms': ("DirRoom1",)})
class TestACL(unittest.TestCase):
    default_mess = Message("DirRoom1")
    default_args = ""

    def setUp(self):
        # Mock self.get_uname_from_mess(mess) to return "Dir1"
        self.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess", return_value="Dir1")

    def tearDown(self):
        del self.get_uname_from_mess

    def test_requires_dir(self):
        self.assertTrue(dir_acl(self, self.default_mess, self.default_args))

    def test_requires_dir_denied(self):
        self.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                  return_value="TestArg")
        self.assertIsNone(dir_acl(self, self.default_mess, self.default_args))

    def test_requires_admin(self):
        self.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                  return_value="Admin1")
        self.assertTrue(admin_acl(self, self.default_mess, self.default_args))

    def test_requires_admin_denied(self):
        self.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                  return_value="TestArg")
        self.assertIsNone(admin_acl(self, self.default_mess, self.default_args))

    def test_requires_dir_chat(self):
        self.assertTrue(dir_acl(self, self.default_mess, self.default_args))

    def test_requires_dir_chat_denied(self):
        self.assertIsNone(dir_acl(self, Message("TestArg"), self.default_args))
