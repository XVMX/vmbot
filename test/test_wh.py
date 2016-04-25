import unittest
import mock

import os

from vmbot.data import WH_DB

from vmbot.wh import Wormhole
from vmbot.utils import EveUtils


class TestWormhole(unittest.TestCase):
    defaultMess = "SenderName"
    defaultArgs = ""

    def setUp(self):
        self.wormhole = Wormhole()
        # Mock self.get_uname_from_mess(mess) to return mess
        self.wormhole.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                           side_effect=lambda arg: arg)
        # Mock self.admins
        self.wormhole.admins = ["Admin"]
        # Dependency hack
        self.wormhole.getSolarSystemData = EveUtils().getSolarSystemData

    def tearDown(self):
        del self.wormhole
        # Delete wh.sqlite after every test case
        try:
            os.remove(WH_DB)
        except:
            pass

    def test_invalid_parameters(self, useDB=True):
        # Create database
        if useDB:
            self.wormhole.wh(self.defaultMess, "add Jita ABC-123 VFK-IV XYZ-789 24")
            self.wormhole.wh(self.defaultMess, "add YA0-XJ DEF-456 Asakai UVW-456 12")
            self.wormhole.wh(self.defaultMess, "add DO6H-Q GHI-789 B-R5RB RST-123 -12")

        # No parameters
        self.assertEqual(self.wormhole.wh(self.defaultMess, self.defaultArgs),
                         "Requires one of list, filter, add or stats as an argument")

        # Missing/excessive parameters
        for param in ["a", "list a", "filter", "filter a", "filter system Jita a", "add",
                      "add Jita", "add Jita ABC-123", "add Jita ABC-123 VFK-IV",
                      "add Jita ABC-123 VFK-IV XYZ-789", "add Jita ABC-123 VFK-IV XYZ-789 10 a",
                      "stats a"]:
            self.assertEqual(self.wormhole.wh(self.defaultMess, param),
                             "wh {} is not an accepted command".format(param))

        # Invalid parameters
        self.assertEqual(self.wormhole.wh(self.defaultMess, "filter TTL a"),
                         "value must be a floating point number when used with TTL")
        self.assertEqual(self.wormhole.wh(self.defaultMess, "add Jita ABC-123 VFK-IV XYZ-789 a"),
                         "TTL must be a floating point number")
        if useDB:
            self.assertEqual(
                self.wormhole.wh(self.defaultMess, "filter a YA0-XJ"),
                ("Jita (ABC-123 | The Forge) <-> VFK-IV (XYZ-789 | Deklein) | About 24h left | "
                 "Scanned by {}<br />YA0-XJ (DEF-456 | Deklein) <-> Asakai (UVW-456 | Black Rise) "
                 "| About 12h left | Scanned by {}").format(self.defaultMess, self.defaultMess)
            )

    def test_no_database(self):
        self.test_invalid_parameters(useDB=False)
        for param in ["list", "filter system Jita", "filter TTL 15", "filter TTL -15", "stats"]:
            self.assertEqual(self.wormhole.wh(self.defaultMess, param), "Error: Data is missing")

    def test_empty_database(self):
        # Create empty database (DB is created but instertion fails because of invalid system name)
        self.assertEqual(
            self.wormhole.wh(self.defaultMess, "add InvalidSystem ABC-123 VFK-IV XYZ-789 24"),
            "Can't find matching systems!"
        )
        self.assertEqual(
            self.wormhole.wh(self.defaultMess, "add Jita ABC-123 InvalidSystem XYZ-789 24"),
            "Can't find matching systems!"
        )

        for param in ["list", "filter system Jita", "filter TTL 15", "filter TTL -15"]:
            self.assertEqual(self.wormhole.wh(self.defaultMess, param), "No connections found")
        self.assertEqual(self.wormhole.wh(self.defaultMess, "stats"),
                         "No connections were added during the last month")

    def test_valid_database(self):
        # Create database and add entries
        self.assertEqual(
            self.wormhole.wh(self.defaultMess, "add Jita ABC-123 VFK-IV XYZ-789 24"),
            "Wormhole from Jita to VFK-IV was added by {}".format(self.defaultMess)
        )
        self.assertEqual(
            self.wormhole.wh(self.defaultMess, "add YA0-XJ DEF-456 Asakai UVW-456 12"),
            "Wormhole from YA0-XJ to Asakai was added by {}".format(self.defaultMess)
        )
        self.assertEqual(
            self.wormhole.wh(self.defaultMess, "add DO6H-Q GHI-789 B-R5RB RST-123 -12"),
            "Wormhole from DO6H-Q to B-R5RB was added by {}".format(self.defaultMess)
        )

        # "wh list" output
        activeConnectionsList = (
            "Jita (ABC-123 | The Forge) <-> VFK-IV (XYZ-789 | Deklein) | About 24h left | "
            "Scanned by {}<br />YA0-XJ (DEF-456 | Deklein) <-> Asakai (UVW-456 | Black Rise) | "
            "About 12h left | Scanned by {}"
        ).format(self.defaultMess, self.defaultMess)

        # "wh filter" output
        singleConnectionList = (
            "Jita (ABC-123 | The Forge) <-> VFK-IV (XYZ-789 | Deklein) | "
            "About 24h left | Scanned by {}"
        ).format(self.defaultMess, self.defaultMess)

        # List all connections
        self.assertEqual(self.wormhole.wh(self.defaultMess, "list"), activeConnectionsList)

        # List connections with Jita as SRC/DEST
        self.assertEqual(self.wormhole.wh(self.defaultMess, "filter system Jita"),
                         singleConnectionList)

        # List connections with >= 15h TTL remaining
        self.assertEqual(self.wormhole.wh(self.defaultMess, "filter TTL 15"),
                         singleConnectionList)

        # List connections with >= -15h TTL remaining
        # Same as list because expired connections are never listed
        self.assertEqual(self.wormhole.wh(self.defaultMess, "filter TTL -15"),
                         activeConnectionsList)

        # Show scanner stats
        self.assertEqual(self.wormhole.wh(self.defaultMess, "stats"),
                         "{}: 3 WH(s)".format(self.defaultMess))

    def test_db_update(self):
        # Create database
        self.wormhole.wh(self.defaultMess, "add Jita ABC-123 VFK-IV XYZ-789 24")

        # Increment db version
        self.wormhole.WH_VERSION += 1

        # Try to add new entry
        self.assertEqual(
            self.wormhole.wh(self.defaultMess, "add YA0-XJ DEF-456 Asakai UVW-456 12"),
            "Tell {} to update the WH database!".format(", ".join(self.wormhole.admins))
        )


if __name__ == "__main__":
    unittest.main()
