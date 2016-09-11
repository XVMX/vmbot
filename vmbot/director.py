# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import xml.etree.ElementTree as ET

import requests

from .botcmd import botcmd
from .helpers.exceptions import APIError

import config


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
    def bcast(self, mess, args):
        """vm <message> - Sends message as a broadcast to your corp

        Must contain less than 10,000 characters (<=10.24kb including the tag line).
        "vm" required to avoid accidental bcasts, only works in director chatrooms.
        Do not abuse this or Solo's wrath shall be upon you.
        """
        if not args.startswith("vm "):
            return None
        broadcast = args[3:]

        if mess.getFrom().getStripped() not in config.JABBER['director_chatrooms']:
            return "Broadcasting is only enabled in director chat"

        sender = self.get_uname_from_mess(mess)
        if sender not in config.DIRECTORS:
            return "You don't have the rights to send broadcasts"

        if len(broadcast) > 10000:
            return "Please limit your broadcast to 10000 characters at once"

        try:
            self._send_bcast(broadcast, sender + " via VMBot")
            return "Your broadcast was sent to " + config.BCAST['target']
        except APIError as e:
            return unicode(e)

    @botcmd
    def pingall(self, mess, args):
        """Pings everyone in the current chatroom"""
        if self.get_uname_from_mess(mess) not in config.DIRECTORS:
            return ":getout:"

        reply = "All hands on {} dick!\n".format(self.get_sender_username(mess))
        reply += ", ".join(self.nick_dict[mess.getFrom().getNode()].keys())
        return reply
