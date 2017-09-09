# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta
import cgi
import xml.etree.ElementTree as ET

import requests
from terminaltables import AsciiTable

from .botcmd import botcmd
from .helpers.exceptions import APIError
from .helpers import database as db
from .helpers.decorators import requires_dir, requires_dir_chat, inject_db
from .helpers.format import format_ref_type
from .models import ISK, WalletJournalEntry

import config

# See https://esi.tech.ccp.is/latest/#!/Wallet
REVENUE_ROWS = (
    ("PVE", ("bounty_prize", "agent_mission_reward", "agent_mission_time_bonus_reward",
             "bounty_prizes", "corporate_reward_payout", "project_discovery_reward")),
    ("POCO", ("planetary_import_tax", "planetary_export_tax")),
    ("Reprocessing", ("reprocessing_tax",)),
    ("Citadel Services", ("office_rental_fee", "factory_slot_rental_fee",
                          "jump_clone_installation_fee", "jump_clone_activation_fee"))
)


class Director(object):
    @staticmethod
    def _send_bcast(broadcast, author):
        # API docs: https://goo.gl/cTYPzg
        messaging = ET.Element("messaging")
        messages = ET.SubElement(messaging, "messages")

        message = ET.SubElement(messages, "message")
        id_ = ET.SubElement(message, "id")
        id_.text = "idc"
        target = ET.SubElement(message, "target")
        target.text = config.BCAST['target']
        sender = ET.SubElement(message, "from")
        sender.text = author
        text = ET.SubElement(message, "text")
        text.text = broadcast

        result = b'<?xml version="1.0"?>' + ET.tostring(messaging)
        headers = {'User-Agent': "XVMX JabberBot",
                   'X-SourceID': config.BCAST['id'],
                   'X-SharedKey': config.BCAST['key']}

        try:
            r = requests.post(config.BCAST['url'], data=result, headers=headers, timeout=5)
            r.raise_for_status()
        except requests.HTTPError as e:
            r = e.response
            res = ET.fromstring(r.content).find(".//response").text
            raise APIError("Broadcast-API returned error code {}: {}".format(r.status_code, res))
        except requests.RequestException as e:
            raise APIError("Error while connecting to Broadcast-API: {}".format(e))

    @botcmd
    @requires_dir_chat
    @requires_dir
    def bcast(self, mess, args):
        """vm <message> - Sends message as a broadcast to your corp

        Must contain less than 10,000 characters (<=10.24kb including the tag line).
        "vm" required to avoid accidental bcasts, only works in director chatrooms.
        Do not abuse this or Solo's wrath shall be upon you.
        """
        if not args.startswith("vm "):
            return None
        broadcast = args[3:]

        if len(broadcast) > 10000:
            return "Please limit your broadcast to 10000 characters at once"

        try:
            self._send_bcast(broadcast, self.get_uname_from_mess(mess) + " via VMBot")
            return "Your broadcast was sent to " + config.BCAST['target']
        except APIError as e:
            return unicode(e)

    @botcmd
    @requires_dir
    def pingall(self, mess, args):
        """Pings everyone in the current chatroom"""
        reply = "All hands on {} dick!\n".format(self.get_sender_username(mess))
        reply += ", ".join(self.nick_dict[mess.getFrom().getNode()].keys())
        return reply

    @staticmethod
    def _wallet_type_query(session):
        query = session.query(WalletJournalEntry.ref_type, db.func.sum(WalletJournalEntry.amount))
        return query.group_by(WalletJournalEntry.ref_type)

    @botcmd
    @requires_dir_chat
    @inject_db
    def revenue(self, mess, args, session):
        """Revenue statistics for the last day/week/month"""
        def to_dict(res):
            return {ref_type: amount for ref_type, amount in res}

        now = datetime.utcnow()
        query = self._wallet_type_query(session).filter(WalletJournalEntry.amount > 0)
        day = to_dict(query.filter(WalletJournalEntry.date > now - timedelta(days=1)).all())
        week = to_dict(query.filter(WalletJournalEntry.date > now - timedelta(weeks=1)).all())
        month = to_dict(query.filter(WalletJournalEntry.date > now - timedelta(days=30)).all())
        genesis = to_dict(query.filter(WalletJournalEntry.date > datetime(2016, 9, 1)).all())

        table = [["Type", "< 24h", "< 1 week", "< 30 days", "Since 2016-09-01"]]
        for name, types in REVENUE_ROWS:
            row = [name]
            for col in (day, week, month, genesis):
                val = 0.0
                for ref_type in types:
                    val += col.get(ref_type, 0.0)
                row.append("{:,.2f} ISK".format(val))
            table.append(row)

        table = AsciiTable(table)
        table.outer_border = False
        table.inner_row_border = True

        res = cgi.escape(table.table).replace('\n', "<br />")
        return '<br /><span style="font-family: monospace;">' + res + "</span>"

    @staticmethod
    def _type_overview(res):
        table = [[format_ref_type(ref_type), "{:,.3f} ISK".format(ISK(total))]
                 for ref_type, total in res]
        table = AsciiTable(table)
        table.outer_border = False
        table.inner_heading_row_border = False
        table.inner_row_border = True

        res = table.table.replace('\n', "<br />")
        return '<br /><span style="font-family: monospace;">' + res + "</span>"

    @botcmd
    @requires_dir_chat
    @inject_db
    def income(self, mess, args, session):
        """Income statistics for the last month"""
        query = self._wallet_type_query(session)
        query = query.filter(WalletJournalEntry.amount > 0,
                             WalletJournalEntry.date > datetime.utcnow() - timedelta(days=30))

        res = sorted(query.all(), key=lambda x: x[1], reverse=True)
        return self._type_overview(res)

    @botcmd
    @requires_dir_chat
    @inject_db
    def expenses(self, mess, args, session):
        """Expense statistics for the last month"""
        query = self._wallet_type_query(session)
        query = query.filter(WalletJournalEntry.amount < 0,
                             WalletJournalEntry.date > datetime.utcnow() - timedelta(days=30))

        res = sorted(query.all(), key=lambda x: x[1])
        return self._type_overview(res)
