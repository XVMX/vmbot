# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime
import xml.etree.ElementTree as ET

from vmbot.models.wallet import WalletJournalEntry

XML_ROW = ('<row date="2016-09-13 12:13:52" refID="13046672950" refTypeID="17" '
           'ownerName1="CONCORD" ownerID1="1000125" ownerName2="ABC" '
           'ownerID2="0" argName1="EVE System" argID1="1" amount="0.99" '
           'balance="1.99" reason="" owner1TypeID="2" owner2TypeID="1373" />')


class TestWalletEntry(unittest.TestCase):
    def test_from_xml_row(self):
        entry = WalletJournalEntry.from_xml_row(ET.fromstring(XML_ROW))

        self.assertEqual(entry.ref_id, 13046672950)
        self.assertEqual(entry.type_id, 17)
        self.assertEqual(entry.amount, 0.99)
        self.assertEqual(entry.date, datetime(2016, 9, 13, 12, 13, 52))


if __name__ == "__main__":
    unittest.main()
