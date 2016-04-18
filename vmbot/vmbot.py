#!/usr/bin/env python
# coding: utf-8

# Copyright (C) 2010 Arthur Furlan <afurlan@afurlan.org>
# Copyright (c) 2013 Sascha J�ngling <sjuengling@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# On Debian systems, you can find the full text of the license in
# /usr/share/common-licenses/GPL-3


from jabberbot import JabberBot, botcmd

import logging
import time
from datetime import datetime
import os
import subprocess
import errno
import signal
from functools import wraps
import random
import re
import xml.etree.ElementTree as ET

import requests
from sympy.parsing.sympy_parser import parse_expr
from sympy.printing.pretty import pretty
import pint

from vmbot_config import config as vmc

from fun import Say, Fun, Chains
from utils import Price, EveUtils
from wh import Wormhole


logger = logging.getLogger("jabberbot")
logger.setLevel(logging.getLevelName(vmc['loglevel']))
logger.addHandler(logging.StreamHandler())


class MUCJabberBot(JabberBot):
    """Add features in JabberBot to allow it to handle specific characteristics of MUCs."""

    # Overriding JabberBot base class
    max_chat_chars = 2000
    PING_FREQUENCY = 60
    PING_TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        self.nick_dict = {}
        super(MUCJabberBot, self).__init__(*args, **kwargs)

    def get_uname_from_mess(self, mess):
        nick = self.get_sender_username(mess)
        node = mess.getFrom().getNode()
        jid = self.nick_dict[node][nick]

        return jid.split('@')[0]

    def callback_presence(self, conn, presence):
        nick = presence.getFrom().getResource()
        node = presence.getFrom().getNode()
        jid = presence.getJid()

        if jid is not None:
            if node not in self.nick_dict:
                self.nick_dict[node] = {}

            if presence.getType() == self.OFFLINE and nick in self.nick_dict[node]:
                del self.nick_dict[node][nick]
            else:
                self.nick_dict[node][nick] = jid

        return super(MUCJabberBot, self).callback_presence(conn, presence)

    def callback_message(self, conn, mess):
        # solodrakban (PM) protection
        # Change this to be limited to certain people if you want by
        # if self.get_sender_username(mess) == "solodrakban":
        if mess.getType() != "groupchat":
            return

        if self.get_sender_username(mess) == vmc['jabber']['nickname']:
            return

        return super(MUCJabberBot, self).callback_message(conn, mess)

    def longreply(self, mess, text, forcePM=False, receiver=None):
        # FIXME: this should be integrated into the default send,
        # forcepm should be part of botcmd
        server = vmc['jabber']['username'].split('@')[1]
        receiver = receiver or self.get_uname_from_mess(mess)

        if len(text) > self.max_chat_chars or forcePM:
            self.send("{}@{}".format(receiver, server), text)
            return True
        else:
            return False

    @botcmd
    def help(self, mess, args):
        reply = super(MUCJabberBot, self).help(mess, args)

        if not args:
            self.longreply(mess, reply, forcePM=True)
            return "Private message sent"
        else:
            # Fix multiline docstring indentation (not compliant to PEP 257)
            reply = '\n'.join([line.lstrip() for line in reply.splitlines()])

            if self.longreply(mess, reply):
                return "Private message sent"
            else:
                return reply


class TimeoutError(Exception):
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)

            return result

        return wrapper

    return decorator


class VMBot(MUCJabberBot, Say, Fun, Chains, Price, EveUtils, Wormhole):
    # Access control lists
    directors = [
        "jack_haydn",
        "thirteen_fish",
        "pimpin_yourhos",
        "johann_tollefson",
        "petyr_baelich",
        "ektony",
        "kairk_efraim",
        "lofac",
        "joker_gates",
        "lordshazbot",
        "borodimer"
    ]
    admins = [
        "joker_gates"
    ]

    # Pubbie talk regex parts
    pubbietalk = [
        "sup",
        "dank",
        "frag",
        "o7",
        "o\/",
        "m8",
        "wot",
        "retart",
        "rekt",
        "toon",
        "iskies",
        "thann(?:y|ies)",
        "murica",
        "yolo",
        "swag",
        "wewlad",
        "fam",
        "rofl",
        "stronk",
        "lmao"
    ]

    def __init__(self, *args, **kwargs):
        self.startupTime = datetime.now()
        self.kmFeedTrigger = time.time() if kwargs.pop('kmFeed', False) else None
        self.newsFeedTrigger = time.time() if kwargs.pop('newsFeed', False) else None

        super(VMBot, self).__init__(*args, **kwargs)

        # Regex to check for zKillboard link
        self.zBotRegex = re.compile("https?:\/\/zkillboard\.com\/kill\/(\d+)\/?", re.IGNORECASE)

        # Regex to check for pubbie talk
        self.pubbieRegex = re.compile("(?:^|\s)(?:{})(?:$|\s)".format('|'.join(self.pubbietalk)),
                                      re.IGNORECASE)
        self.pubbieKicked = set()

        # Initialize asynchronous commands
        if self.kmFeedTrigger:
            try:
                self.kmFeedID = requests.get(
                    "https://zkillboard.com/api/losses/corporationID/2052404106/"
                    "limit/1/no-items/no-attackers/",
                    headers={'User-Agent': "XVMX JabberBot"}, timeout=5
                ).json()[0]['killID']
            except (requests.exceptions.RequestException, ValueError):
                self.kmFeedTrigger = None

        if self.newsFeedTrigger:
            self.newsFeedIDs = {'news': None, 'devblog': None}

    def idle_proc(self):
        """Execute asynchronous commands."""
        if self.kmFeedTrigger and self.kmFeedTrigger <= time.time():
            self.kmFeed()
            self.kmFeedTrigger += 5 * 60

        if self.newsFeedTrigger and self.newsFeedTrigger <= time.time():
            self.newsFeed()
            self.newsFeedTrigger += 60 * 60

        return super(VMBot, self).idle_proc()

    def callback_presence(self, conn, presence):
        reply = super(VMBot, self).callback_presence(conn, presence)

        jid = presence.getJid()
        type_ = presence.getType()
        if jid is not None and type_ == self.AVAILABLE:
            nick = presence.getFrom().getResource()
            room = presence.getFrom().getStripped()
            uname = jid.split('@')[0]

            if uname in self.pubbieKicked and room == vmc['jabber']['chatroom1']:
                self.pubbieKicked.remove(uname)
                self.send(vmc['jabber']['chatroom1'], "{}: Talk shit, get hit".format(nick),
                          message_type="groupchat")
        elif type_ == self.OFFLINE and presence.getStatusCode() == "307":
            self.pubbieKicked.add(jid.split('@')[0])

        return reply

    def callback_message(self, conn, mess):
        reply = super(VMBot, self).callback_message(conn, mess)

        # See XEP-0203: Delayed Delivery (http://xmpp.org/extensions/xep-0203.html)
        fromHist = "urn:xmpp:delay" in mess.getProperties()

        message = mess.getBody()
        room = mess.getFrom().getStripped()

        if message and self.get_sender_username(mess) != vmc['jabber']['nickname'] and not fromHist:
            if self.pubbieRegex.search(message) is not None and room == vmc['jabber']['chatroom1']:
                self.muc_kick(room, self.get_sender_username(mess),
                              "Emergency pubbie broadcast system")

            if not message.lower().startswith("zbot"):
                uniqueMatches = {match.group(0) for match in self.zBotRegex.finditer(message)}
                zBotReplies = [self.zbot(mess, "{} compact".format(match))
                               for match in uniqueMatches]
                if zBotReplies:
                    self.send_simple_reply(mess, "<br />".join(zBotReplies))

        return reply

    @botcmd
    def math(self, mess, args):
        """<expr> - Evaluates expr mathematically

        Force floating point numbers by doing 4.0/3 instead of 4/3
        """
        @timeout(10, "Sorry, this query took too long to execute and I had to kill it off")
        def do_math(args):
            return pretty(parse_expr(args), full_prec=False, use_unicode=False)

        try:
            reply = do_math(args)
        except Exception as e:
            return str(e)

        if '\n' in reply:
            reply = "\n{}".format(reply)
        reply = '<font face="monospace">{}</font>'.format(
            reply.replace('\n', '</font><br/><font face="monospace">')
        )

        if len(reply) > self.max_chat_chars:
            return "I've evaluated your expression but it's too long to send in a groupchat"

        return reply

    @botcmd
    def convert(self, mess, args):
        """<amount> <source> to <destination> - Converts amount from source to destination"""
        src, dst = args.split(" to ", 1)
        ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

        try:
            return str(ureg(src).to(dst))
        except pint.unit.DimensionalityError as e:
            return str(e)
        except Exception as e:
            return "Failed to convert your request: {}".format(e)

    @botcmd
    def dice(self, mess, args):
        """[dice count] [sides] - Roll the dice. Defaults to one dice and six sides"""
        if len(args) > 2:
                return "You need to provide none, one or two parameters"

        dice = 1
        sides = 6
        args = args.split()
        try:
            dice = int(args[0])
            sides = int(args[1])
        except ValueError:
            return "You need to provide integer parameters"
        except IndexError:
            pass

        if not 1 <= dice <= 50:
            return "That's an absurd number of dice, try again"
        if not 1 <= sides <= 256:
            return "That's an absurd number of sides, try again"

        return "I rolled {} dice with {} sides each. The result is [{}]".format(
            dice, sides, "][".join(map(str, [random.randint(1, sides) for i in xrange(dice)]))
        )

    @botcmd
    def roll(self, mess, args):
        """Displays a random number between 1 and 100"""
        return str(random.randint(1, 100))

    @botcmd
    def flipcoin(self, mess, args):
        """Flips a coin"""
        return random.choice(["Heads!", "Tails!"])

    @botcmd
    def pickone(self, mess, args):
        """<option1> or <option2> [or <option3> ...] - Chooses an option for you"""
        args = args.strip().split(" or ")

        if len(args) > 1:
            return random.choice(args)
        else:
            return "You need to provide at least 2 options to choose from"

    @botcmd
    def ping(self, mess, args):
        """[-a] - Is this thing on? The -a flag makes the bot answer to you specifically"""
        if args == "-a":
            return "{}: Pong".format(self.get_sender_username(mess))
        else:
            return "Pong"

    @botcmd
    def bcast(self, mess, args):
        """vm <message> - Sends a broadcast to XVMX members

        Must be <=10.24kb including the tag line.
        "vm" required to avoid accidental bcasts, only works in dir chat.
        Do not abuse this or Solo's wrath shall be upon you.
        """
        def sendBcast(broadcast, author):
            # API docs: http://goo.gl/cTYPzg
            messaging = ET.Element("messaging")
            messages = ET.SubElement(messaging, "messages")
            message = ET.SubElement(messages, "message")
            id = ET.SubElement(message, "id")
            id.text = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            target = ET.SubElement(message, "target")
            target.text = vmc['bcast']['target']
            sender = ET.SubElement(message, "from")
            sender.text = author
            text = ET.SubElement(message, "text")
            text.text = broadcast
            result = '<?xml version="1.0"?>' + ET.tostring(messaging)

            try:
                r = requests.post(
                    vmc['bcast']['url'], data=result,
                    headers={'User-Agent': "XVMX JabberBot",
                             'X-SourceID': vmc['bcast']['id'], 'X-SharedKey': vmc['bcast']['key']},
                    timeout=10
                )
                return r.status_code
            except requests.exceptions.RequestException as e:
                return str(e)

        if args[:2] != "vm" or len(args) <= 3:
            return None

        if str(mess.getFrom()).split('@')[0] != "vm_dir":
            return "Broadcasting is only enabled in director chat"

        sender = self.get_uname_from_mess(mess)
        if sender not in self.directors:
            return "You don't have the rights to send broadcasts"

        broadcast = args[3:]

        if len(broadcast) > 10240:
            return ("This broadcast has {} characters and is too long; "
                    "max length is 10240 characters. Please try again with less of a tale. "
                    "You could try, y'know, a forum post.").format(len(broadcast))

        status = sendBcast(broadcast, "{} via VMBot".format(sender))
        if status == 200:
            return "{}, I have sent your broadcast to {}".format(self.get_sender_username(mess),
                                                                 vmc['bcast']['target'])
        elif isinstance(status, str):
            return "Error while connecting to Broadcast-API: {}".format(status)
        else:
            return "Broadcast-API returned error code {}".format(status)

    @botcmd
    def pingall(self, mess, args):
        """Pings everyone in the current MUC room"""
        if self.get_uname_from_mess(mess) not in self.directors:
            return ":getout:"

        reply = "All hands on {} dick!\n".format(self.get_sender_username(mess))
        reply += ", ".join(self.nick_dict[mess.getFrom().getNode()].keys())
        return reply

    @botcmd
    def uptime(self, mess, args):
        """Displays for how long the bot is running already"""
        return "arc_codie has a server, but it hasn't been up as long as {}".format(
            datetime.now() - self.startupTime
        )

    @botcmd(hidden=True)
    def reload(self, mess, args):
        """Kills the bot's process

        If ran in a while true loop on the shell, it'll immediately reconnect.
        """
        if not args:
            if self.get_uname_from_mess(mess) in self.admins:
                self.quit()
                return "afk shower"
            else:
                return "You are not authorized to reload the bot, please go and DIAF!"

    @botcmd(hidden=True)
    def gitpull(self, mess, args):
        """Pulls the latest commit from the bot repository and updates the bot with it"""
        if str(mess.getFrom()).split("@")[0] != "vm_dir":
            return "git pull is only enabled in director chat"

        if self.get_uname_from_mess(mess) not in self.admins:
            return "You are not allowed to git pull"

        path = os.path
        p = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=path.abspath(path.join(path.dirname(__file__), os.pardir)))
        out, err = p.communicate()
        return "{}\n{}".format(out, err).strip()


if __name__ == "__main__":
    # Grabbing values from imported config file
    jbc = vmc['jabber']
    morgooglie = VMBot(jbc['username'], jbc['password'], jbc['res'], kmFeed=True, newsFeed=True)
    morgooglie.muc_join_room(jbc['chatroom1'], jbc['nickname'])
    morgooglie.muc_join_room(jbc['chatroom2'], jbc['nickname'])
    morgooglie.muc_join_room(jbc['chatroom3'], jbc['nickname'])
    morgooglie.serve_forever()
