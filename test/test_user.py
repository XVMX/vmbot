# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime, timedelta

from vmbot.models.user import User, Nickname


class TestUser(unittest.TestCase):
    def setUp(self):
        self.user = User("user@domain.tld")
        self.user.nicks = [Nickname("nick"), Nickname("ABC")]

    def tearDown(self):
        del self.user

    def test_uname(self):
        self.assertEqual(self.user.uname, "user")

    def test_last_seen(self):
        self.user.nicks[0].last_seen += timedelta(days=1)
        self.assertGreater(self.user.last_seen, datetime.utcnow())

        nonick_usr = User("user2@domain.tld")
        self.assertIsNone(nonick_usr.last_seen)


class TestNickname(unittest.TestCase):
    def setUp(self):
        self.nick = Nickname("nick")

    def tearDown(self):
        del self.nick

    def test_nick(self):
        self.assertEqual(self.nick.nick, "nick")


if __name__ == "__main__":
    unittest.main()
