# coding: utf-8

import unittest
import mock

import os

from vmbot.helpers.files import WH_DB

from vmbot.wh import Wormhole


class TestWormhole(unittest.TestCase):
    default_mess = "SenderName"
    default_args = ""

    def setUp(self):
        self.wormhole = Wormhole()
        # Mock self.get_uname_from_mess(mess) to return mess
        self.wormhole.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                           side_effect=lambda arg: arg)
        # Mock VMBot.ADMINS
        self.wormhole.ADMINS = ("Admin",)

    def tearDown(self):
        del self.wormhole
        self.setUpClass()

    @classmethod
    def setUpClass(cls):
        try:
            os.remove(WH_DB)
        except OSError:
            pass

    def test_invalid_parameters(self, use_db=True):
        # Create database
        if use_db:
            self.wormhole.wh(self.default_mess, "add Jita ABC-123 VFK-IV XYZ-789 24")
            self.wormhole.wh(self.default_mess, "add YA0-XJ DEF-456 Asakai UVW-456 12")
            self.wormhole.wh(self.default_mess, "add DO6H-Q GHI-789 B-R5RB RST-123 -12")

        # No parameters
        self.assertEqual(self.wormhole.wh(self.default_mess, self.default_args),
                         "Requires one of list, filter, add or stats as an argument")

        # Missing/excessive parameters
        for param in ("a", "list a", "filter", "filter a", "filter system Jita a", "add",
                      "add Jita", "add Jita ABC-123", "add Jita ABC-123 VFK-IV",
                      "add Jita ABC-123 VFK-IV XYZ-789", "add Jita ABC-123 VFK-IV XYZ-789 10 a",
                      "stats a"):
            self.assertEqual(self.wormhole.wh(self.default_mess, param),
                             "wh {} is not an accepted command".format(param))

        # Invalid parameters
        self.assertEqual(self.wormhole.wh(self.default_mess, "filter TTL a"),
                         "value must be a floating point number when used with TTL")
        self.assertEqual(self.wormhole.wh(self.default_mess, "add Jita ABC-123 VFK-IV XYZ-789 a"),
                         "TTL must be a floating point number")
        if use_db:
            self.assertEqual(
                self.wormhole.wh(self.default_mess, "filter a YA0-XJ"),
                ("Jita (ABC-123 | The Forge) <-> VFK-IV (XYZ-789 | Deklein) | About 24h left | "
                 "Scanned by {}<br />YA0-XJ (DEF-456 | Deklein) <-> Asakai (UVW-456 | Black Rise) "
                 "| About 12h left | Scanned by {}").format(self.default_mess, self.default_mess)
            )

    def test_no_database(self):
        self.test_invalid_parameters(use_db=False)

        for param in ("list", "filter system Jita", "filter TTL 15", "filter TTL -15", "stats"):
            self.assertEqual(self.wormhole.wh(self.default_mess, param), "Error: Data is missing")

    def test_empty_database(self):
        # Create empty database (DB is created but instertion fails because of invalid system name)
        self.assertEqual(
            self.wormhole.wh(self.default_mess, "add InvalidSystem ABC-123 VFK-IV XYZ-789 24"),
            "Can't find matching systems!"
        )
        self.assertEqual(
            self.wormhole.wh(self.default_mess, "add Jita ABC-123 InvalidSystem XYZ-789 24"),
            "Can't find matching systems!"
        )

        for param in ("list", "filter system Jita", "filter TTL 15", "filter TTL -15"):
            self.assertEqual(self.wormhole.wh(self.default_mess, param), "No connections found")

        self.assertEqual(self.wormhole.wh(self.default_mess, "stats"),
                         "No connections were added during the last month")

    def test_valid_database(self):
        # Create database and add entries
        self.assertEqual(
            self.wormhole.wh(self.default_mess, "add Jita ABC-123 VFK-IV XYZ-789 24"),
            "Wormhole from Jita to VFK-IV was added by {}".format(self.default_mess)
        )
        self.assertEqual(
            self.wormhole.wh(self.default_mess, "add YA0-XJ DEF-456 Asakai UVW-456 12"),
            "Wormhole from YA0-XJ to Asakai was added by {}".format(self.default_mess)
        )
        self.assertEqual(
            self.wormhole.wh(self.default_mess, "add DO6H-Q GHI-789 B-R5RB RST-123 -12"),
            "Wormhole from DO6H-Q to B-R5RB was added by {}".format(self.default_mess)
        )

        # "wh list" output
        active_connections_list = (
            "Jita (ABC-123 | The Forge) <-> VFK-IV (XYZ-789 | Deklein) | About 24h left | "
            "Scanned by {}<br />YA0-XJ (DEF-456 | Deklein) <-> Asakai (UVW-456 | Black Rise) | "
            "About 12h left | Scanned by {}"
        ).format(self.default_mess, self.default_mess)

        # "wh filter" output
        single_connection_list = (
            "Jita (ABC-123 | The Forge) <-> VFK-IV (XYZ-789 | Deklein) | "
            "About 24h left | Scanned by {}"
        ).format(self.default_mess, self.default_mess)

        # List all connections
        self.assertEqual(self.wormhole.wh(self.default_mess, "list"), active_connections_list)

        # List connections with Jita as SRC/DEST
        self.assertEqual(self.wormhole.wh(self.default_mess, "filter system Jita"),
                         single_connection_list)

        # List connections with >= 15h TTL remaining
        self.assertEqual(self.wormhole.wh(self.default_mess, "filter TTL 15"),
                         single_connection_list)

        # List connections with >= -15h TTL remaining
        # Same as list because expired connections are never listed
        self.assertEqual(self.wormhole.wh(self.default_mess, "filter TTL -15"),
                         active_connections_list)

        # Show scanner stats
        self.assertEqual(self.wormhole.wh(self.default_mess, "stats"),
                         "{}: 3 WH(s)".format(self.default_mess))

    def test_database_update(self):
        # Create database
        self.wormhole.wh(self.default_mess, "add Jita ABC-123 VFK-IV XYZ-789 24")

        # Increment db version
        self.wormhole.WH_VERSION += 1

        # Try to add new entry
        self.assertEqual(
            self.wormhole.wh(self.default_mess, "add YA0-XJ DEF-456 Asakai UVW-456 12"),
            "Tell {} to update the WH database!".format(", ".join(self.wormhole.ADMINS))
        )


if __name__ == "__main__":
    unittest.main()
