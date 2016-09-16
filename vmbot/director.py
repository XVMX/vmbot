# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta
import cgi
import xml.etree.ElementTree as ET

import requests
from terminaltables import SingleTable

from .botcmd import botcmd
from .helpers.exceptions import APIError
from .helpers import database as db
from .helpers.decorators import requires_dir, requires_dir_chat
from .models import WalletJournalEntry

import config

# See https://api.eveonline.com/eve/RefTypes.xml.aspx
REF_REVENUE = (
    # Bounties, Mission Rewards, Incursions, Project Discovery
    ("PVE", (17, 33, 34, 85, 99, 125)),
    # Planetary Import/Export Tax
    ("POCO", (96, 97)),
    # Reprocessing Tax
    ("Reprocessing", (127,)),
    # Office Rental Fee, Factory Slot Rental Fee, # Jump Clone Fees
    ("Citadel Services", (13, 14, 55, 128))
)


class Director(object):
    @staticmethod
    def _send_bcast(broadcast, author):
        # API docs: http://goo.gl/cTYPzg
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
        except requests.exceptions.RequestException as e:
            raise APIError("Error while connecting to Broadcast-API: {}".format(e))

        if r.status_code != 200:
            res = ET.fromstring(r.content).find(".//response").text
            raise APIError("Broadcast-API returned error code {}: {}".format(r.status_code, res))

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

    @botcmd
    @requires_dir_chat
    def revenue(self, mess, args):
        """Revenue statistics for the last day/week/month"""
        def to_dict(res):
            return {type_id: amount for type_id, amount in res}

        session = db.Session()
        query = session.query(WalletJournalEntry.type_id, db.func.sum(WalletJournalEntry.amount))
        query = query.filter(WalletJournalEntry.amount > 0).group_by(WalletJournalEntry.type_id)

        now = datetime.utcnow()
        day = to_dict(query.filter(WalletJournalEntry.date > now - timedelta(days=1)).all())
        week = to_dict(query.filter(WalletJournalEntry.date > now - timedelta(weeks=1)).all())
        month = to_dict(query.filter(WalletJournalEntry.date > now - timedelta(days=30)).all())

        session.close()

        table = [["Type", "< 24h", "< 1 week", "< 30 days"]]
        for name, types in REF_REVENUE:
            row = [name]
            for col in (day, week, month):
                val = 0.0
                for type_id in types:
                    val += col.get(type_id, 0.0)
                row.append("{:,.2f} ISK".format(val))
            table.append(row)

        table = SingleTable(table)
        table.outer_border = False
        table.inner_row_border = True

        res = cgi.escape(table.table).replace('\n', "<br />")
        return '<br /><span style="font-family: monospace;">' + res + "</span>"

