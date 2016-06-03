import unittest

import os

from vmbot.helpers.files import CONFIG

from vmbot.config import config


@unittest.skipUnless(os.path.isfile(CONFIG), "Config file not found")
class TestConfig(unittest.TestCase):
    def test_loglevel(self):
        self.assertIsInstance(config['loglevel'], str)

    def test_username(self):
        self.assertIsInstance(config['jabber']['username'], str)

    def test_password(self):
        self.assertIsInstance(config['jabber']['password'], str)

    def test_resource(self):
        self.assertIsInstance(config['jabber']['res'], str)

    def test_nickname(self):
        self.assertIsInstance(config['jabber']['nickname'], str)

    def test_chatrooms(self):
        self.assertIsInstance(config['jabber']['chatrooms'], tuple)
        for room in config['jabber']['chatrooms']:
            self.assertIsInstance(room, str)

    def test_bcast_url(self):
        self.assertIsInstance(config['bcast']['url'], str)

    def test_bcast_id(self):
        self.assertIsInstance(config['bcast']['id'], str)

    def test_bcast_key(self):
        self.assertIsInstance(config['bcast']['key'], str)

    def test_bcast_target(self):
        self.assertIsInstance(config['bcast']['target'], str)

    def test_blacklist_url(self):
        self.assertIsInstance(config['blacklist']['url'], str)

    def test_blacklist_key(self):
        self.assertIsInstance(config['blacklist']['key'], str)


if __name__ == "__main__":
    unittest.main()
