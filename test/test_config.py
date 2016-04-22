import unittest

from vmbot.config import config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.config = config

    def tearDown(self):
        del self.config

    def test_loglevel(self):
        self.assertEqual(self.config['loglevel'], "INFO")

    def test_username(self):
        self.assertEqual(self.config['jabber']['username'], "username@domain.tld")

    def test_password(self):
        self.assertEqual(self.config['jabber']['password'], "yourpassword")

    def test_resource(self):
        self.assertEqual(self.config['jabber']['res'], "VMBot")

    def test_nickname(self):
        self.assertEqual(self.config['jabber']['nickname'], "BotNickname")

    def test_chatrooms(self):
        self.assertEqual(self.config['jabber']['chatrooms'][0], "room1@conference.domain.tld")
        self.assertEqual(self.config['jabber']['chatrooms'][1], "room2@conference.domain.tld")
        self.assertEqual(self.config['jabber']['chatrooms'][2], "room3@conference.domain.tld")

    def test_bcast_url(self):
        self.assertEqual(self.config['bcast']['url'], "")

    def test_bcast_id(self):
        self.assertEqual(self.config['bcast']['id'], "")

    def test_bcast_key(self):
        self.assertEqual(self.config['bcast']['key'], "")

    def test_bcast_target(self):
        self.assertEqual(self.config['bcast']['target'], "")

    def test_blacklist_url(self):
        self.assertEqual(self.config['blacklist']['url'], "")

    def test_blacklist_key(self):
        self.assertEqual(self.config['blacklist']['key'], "")


if __name__ == "__main__":
    unittest.main()
