# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta
import cgi
import xml.etree.ElementTree as ET

import pyotp
from terminaltables import AsciiTable

from .botcmd import botcmd
from .helpers.exceptions import APIError, APIStatusError
from .helpers import database as db
from .helpers import api
from .helpers.decorators import requires_role, requires_dir_chat, inject_db
from .helpers.format import format_ref_type
from .models import ISK, WalletJournalEntry

import config

REVENUE_COLS = (
    ("< 24h", timedelta(days=1)), ("< 1 week", timedelta(weeks=1)),
    ("< 30 days", timedelta(days=30))
) + config.REVENUE_COLS

# See https://esi.evetech.net/ui/#/Wallet
REVENUE_ROWS = (
    ("PVE", ("agent_mission_reward", "agent_mission_time_bonus_reward", "bounty_prize",
             "bounty_prizes", "corporate_reward_payout", "project_discovery_reward")),
    ("POCO", ("planetary_import_tax", "planetary_export_tax")),
    ("Citadel Services", ("docking_fee", "office_rental_fee", "factory_slot_rental_fee",
                          "reprocessing_tax", "brokers_fee", "structure_gate_jump",
                          "jump_clone_installation_fee", "jump_clone_activation_fee"))
)


class Director(object):
    @staticmethod
    def _send_bcast(target, broadcast, author):
        # API docs: https://goo.gl/cTYPzg
        messaging = ET.Element("messaging")
        messages = ET.SubElement(messaging, "messages")

        message = ET.SubElement(messages, "message")
        id_ = ET.SubElement(message, "id")
        id_.text = "idc"
        tgt = ET.SubElement(message, "target")
        tgt.text = target
        sender = ET.SubElement(message, "from")
        sender.text = author
        text = ET.SubElement(message, "text")
        text.text = broadcast

        result = b'<?xml version="1.0"?>' + ET.tostring(messaging)
        headers = {'X-SourceID': config.BCAST['id'], 'X-SharedKey': config.BCAST['key']}
        api.request_api(config.BCAST['url'], data=result, headers=headers, timeout=5, method="POST")

    @botcmd(disable_if=not config.BCAST['key'])
    @requires_dir_chat
    @requires_role("director")
    def bcast(self, mess, args):
        """<target> <message> - Sends message as a broadcast to target

        Must contain less than 10,000 characters (<=10.24kb including the tag line).
        target must be one of the keys specified in the configuration. Omit all arguments
        to see a list of permitted targets. Restricted to director chatrooms.
        Do not abuse this or Solo's wrath shall be upon you.
        """
        try:
            target, broadcast = args.split(None, 1)
            target = config.BCAST['targets'][target.lower()]
        except (ValueError, KeyError):
            return ("Missing or invalid target. Valid targets are: "
                    + ", ".join(config.BCAST['targets'].keys()))

        if len(broadcast) > 10000:
            return "Please limit your broadcast to 10000 characters at once"

        try:
            self._send_bcast(target, broadcast, self.get_uname_from_mess(mess) + " via VMBot")
            return "Your broadcast was sent to " + target
        except APIStatusError as e:
            r = e.response
            res = ET.fromstring(r.content).find(".//response").text
            return unicode(e) + ": " + res
        except APIError as e:
            return unicode(e)

    @botcmd
    @requires_role("director")
    def pingall(self, mess, args):
        """Pings everyone in the current chatroom"""
        reply = "All hands on {} dick!\n".format(self.get_sender_username(mess))
        reply += ", ".join(self.nick_dict[mess.getFrom().getNode()].keys())
        return reply

    @botcmd(hidden=True, force_pm=True)
    @requires_role("token")
    def token(self, mess, args):
        """<account> - Generates the current login code for account"""
        args = args.strip().lower()
        if args not in config.TOTP_KEYS:
            return "This account is not available for code generation"

        totp = pyotp.TOTP(config.TOTP_KEYS[args])
        return totp.now()

    @staticmethod
    def _wallet_type_query(session):
        query = session.query(WalletJournalEntry.ref_type, db.func.sum(WalletJournalEntry.amount))
        return query.group_by(WalletJournalEntry.ref_type)

    @botcmd(disable_if=not config.REVENUE_TRACKING)
    @inject_db
    @requires_dir_chat
    def revenue(self, mess, args, session):
        """Revenue statistics for the last day/week/month"""
        data = []
        table = [["Type"]]
        now = datetime.utcnow()
        query = self._wallet_type_query(session).filter(WalletJournalEntry.amount > 0)

        for title, from_date in REVENUE_COLS:
            table[0].append(title)

            if isinstance(from_date, timedelta):
                from_date = now - from_date
            data.append(dict(query.filter(WalletJournalEntry.date > from_date).all()))

        for name, types in REVENUE_ROWS:
            row = [name]
            for col in data:
                val = sum(col.get(ref_type, 0.0) for ref_type in types)
                row.append("{:,.2f} ISK".format(val))
            table.append(row)

        table = AsciiTable(table)
        table.outer_border = False
        table.inner_row_border = True

        res = cgi.escape(table.table).replace('\n', "<br />")
        return '<br /><span style="font-family: monospace;">' + res + "</span>"

    @staticmethod
    def _type_overview(res):
        table = [[format_ref_type(ref_type), "{:,.2f} ISK".format(ISK(total))]
                 for ref_type, total in res]
        table = AsciiTable(table)
        table.outer_border = False
        table.inner_heading_row_border = False
        table.inner_row_border = True

        res = table.table.replace('\n', "<br />")
        return '<br /><span style="font-family: monospace;">' + res + "</span>"

    @botcmd(disable_if=not config.REVENUE_TRACKING)
    @inject_db
    @requires_dir_chat
    def income(self, mess, args, session):
        """Income statistics for the last month"""
        query = self._wallet_type_query(session)
        query = query.filter(WalletJournalEntry.amount > 0,
                             WalletJournalEntry.date > datetime.utcnow() - timedelta(days=30))

        res = sorted(query.all(), key=lambda x: x[1], reverse=True)
        return self._type_overview(res)

    @botcmd(disable_if=not config.REVENUE_TRACKING)
    @inject_db
    @requires_dir_chat
    def expenses(self, mess, args, session):
        """Expense statistics for the last month"""
        query = self._wallet_type_query(session)
        query = query.filter(WalletJournalEntry.amount < 0,
                             WalletJournalEntry.date > datetime.utcnow() - timedelta(days=30))

        res = sorted(query.all(), key=lambda x: x[1])
        return self._type_overview(res)
