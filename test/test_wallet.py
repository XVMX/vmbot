# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from datetime import datetime

from vmbot.models.wallet import WalletJournalEntry


class TestWalletEntry(unittest.TestCase):
    def test_from_esi_record(self):
        rec = {"ref_id": 14541533899, "ref_type": "bounty_prizes",
               "amount": 1754495.63, "date": "2017-09-07T20:43:22Z"}
        entry = WalletJournalEntry.from_esi_record(rec)

        self.assertEqual(entry.ref_id, 14541533899)
        self.assertEqual(entry.ref_type, "bounty_prizes")
        self.assertEqual(entry.amount, 1754495.63)
        self.assertEqual(entry.date, datetime(2017, 9, 7, 20, 43, 22))


if __name__ == "__main__":
    unittest.main()
