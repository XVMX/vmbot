import unittest

import os

from vmbot.helpers.files import CONFIG

from vmbot.config import config


@unittest.skipUnless(os.path.isfile(CONFIG), "Config file not found")
class TestConfig(unittest.TestCase):
    def test_loglevel(self):
        self.assertEqual(config['loglevel'], "INFO")

    def test_username(self):
        self.assertEqual(config['jabber']['username'], "username@domain.tld")

    def test_password(self):
        self.assertEqual(config['jabber']['password'], "yourpassword")

    def test_resource(self):
        self.assertEqual(config['jabber']['res'], "VMBot")

    def test_nickname(self):
        self.assertEqual(config['jabber']['nickname'], "BotNickname")

    def test_chatrooms(self):
        self.assertEqual(config['jabber']['chatrooms'][0], "room1@conference.domain.tld")
        self.assertEqual(config['jabber']['chatrooms'][1], "room2@conference.domain.tld")
        self.assertEqual(config['jabber']['chatrooms'][2], "room3@conference.domain.tld")

    def test_bcast_url(self):
        self.assertEqual(config['bcast']['url'], "")

    def test_bcast_id(self):
        self.assertEqual(config['bcast']['id'], "")

    def test_bcast_key(self):
        self.assertEqual(config['bcast']['key'], "")

    def test_bcast_target(self):
        self.assertEqual(config['bcast']['target'], "")

    def test_blacklist_url(self):
        self.assertEqual(config['blacklist']['url'], "")

    def test_blacklist_key(self):
        self.assertEqual(config['blacklist']['key'], "")


if __name__ == "__main__":
    unittest.main()
