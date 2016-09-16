# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
from datetime import datetime
from os import path, pardir
import subprocess
import random

from xmpp.protocol import JID
from .jabberbot import JabberBot
from sympy.parsing.sympy_parser import parse_expr
from sympy.printing.pretty import pretty
import pint

from .botcmd import botcmd
from .director import Director
from .fun import Say, Fun, Chains
from .utils import Price, EVEUtils
from .helpers.exceptions import TimeoutError
from .helpers import database as db
from .helpers import api
from .helpers.decorators import timeout, requires_admin, requires_dir_chat
from .helpers.regex import PUBBIE_REGEX, ZKB_REGEX
from .models.messages import Message

import config


class MUCJabberBot(JabberBot):
    """Add features in JabberBot to allow it to handle specific characteristics of MUCs."""

    # Overriding JabberBot base class
    MAX_CHAT_CHARS = 1000
    PING_FREQUENCY = 60
    PING_TIMEOUT = 5

    def __init__(self, username, password, res, *args, **kwargs):
        self.nick_dict = {}
        super(MUCJabberBot, self).__init__(username, password, res, *args, **kwargs)
        self.jid.setResource(res)

    def get_uname_from_mess(self, mess, full_jid=False):
        nick = self.get_sender_username(mess)
        node = mess.getFrom().getNode()

        # Private message
        if nick == node:
            return mess.getFrom() if full_jid else nick

        # MUC message
        try:
            jid = self.nick_dict[node][nick]
        except KeyError:
            jid = JID("default")

        return jid if full_jid else jid.getNode()

    def send_simple_reply(self, mess, text, private=False):
        cmd = mess.getBody().split(' ', 1)[0].lower()
        cmd = self.commands.get(cmd, None)

        if len(text) > self.MAX_CHAT_CHARS or getattr(cmd, "_vmbot_forcepm", False):
            self.send_message(self.build_reply(mess, text, private=True))
            text = "Private message sent"

        return super(MUCJabberBot, self).send_simple_reply(mess, text, private)

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
                self.nick_dict[node][nick] = JID(jid)

        return super(MUCJabberBot, self).callback_presence(conn, presence)

    def callback_message(self, conn, mess):
        # solodrakban (PM) protection
        # Discard non-groupchat messages
        if mess.getType() != "groupchat":
            return

        # Discard messages from myself
        if self.get_uname_from_mess(mess, full_jid=True) == self.jid:
            return

        return super(MUCJabberBot, self).callback_message(conn, mess)

    @botcmd
    def help(self, mess, args):
        # Fix multiline docstring indentation (not compliant to PEP 257)
        reply = super(MUCJabberBot, self).help(mess, args)
        return '\n'.join(line.lstrip() for line in reply.splitlines())

    @botcmd
    def nopm(self, mess, args):
        """<command> [args] - Forces command to be sent to the channel"""
        if ' ' in args:
            cmd, args = args.split(' ', 1)
        else:
            cmd, args = args, ""
        cmd = cmd.lower()

        if cmd in self.commands:
            super(MUCJabberBot, self).send_simple_reply(mess, self.commands[cmd](mess, args))


class VMBot(MUCJabberBot, Director, Say, Fun, Chains, Price, EVEUtils):
    def __init__(self, *args, **kwargs):
        self.startup_time = datetime.utcnow()
        self.message_trigger = time.time() + 30 if kwargs.pop('feeds', False) else None

        super(VMBot, self).__init__(*args, **kwargs)

    def idle_proc(self):
        """Retrieve and send stored messages."""
        if self.message_trigger and self.message_trigger <= time.time():
            sess = db.Session()

            for mess in sess.query(Message).order_by(Message.message_id.asc()).all():
                self.send(**mess.send_dict)
                sess.delete(mess)

            sess.commit()
            sess.close()
            self.message_trigger += 60

        return super(VMBot, self).idle_proc()

    def callback_message(self, conn, mess):
        reply = super(VMBot, self).callback_message(conn, mess)

        # See XEP-0203: Delayed Delivery (http://xmpp.org/extensions/xep-0203.html)
        if (self.get_uname_from_mess(mess, full_jid=True) == self.jid or
                mess.getType() != "groupchat" or "urn:xmpp:delay" in mess.getProperties()):
            return reply

        msg = mess.getBody()
        room = mess.getFrom().getStripped()

        if msg:
            # Pubbie smacktalk
            if PUBBIE_REGEX.search(msg) is not None and room in config.JABBER['primary_chatrooms']:
                super(MUCJabberBot, self).send_simple_reply(mess, self.pubbiesmack(mess))

            # zBot
            matches = {match.group(1) for match in ZKB_REGEX.finditer(msg)}
            replies = [api.zbot(match) for match in matches]
            if replies:
                super(MUCJabberBot, self).send_simple_reply(mess, '\n'.join(replies))

        return reply

    @botcmd
    def math(self, mess, args):
        """<expr> - Evaluates expr mathematically"""
        @timeout(5, "Your calculation is too expensive and was killed off")
        def do_math(args):
            return pretty(parse_expr(args), full_prec=False, use_unicode=True)

        try:
            reply = do_math(args)
        except TimeoutError as e:
            return unicode(e)
        except Exception as e:
            return "Failed to calculate your request: {}".format(e)

        reply = '<span style="font-family: monospace;">' + reply.replace('\n', "<br />") + "</span>"
        if "<br />" in reply:
            reply = "<br />" + reply

        return reply

    @botcmd
    def convert(self, mess, args):
        """<amount> <source> to <destination> - Converts amount from source to destination"""
        try:
            src, dest = args.split(" to ", 1)
        except ValueError:
            return "Please provide a source unit/amount and a destination unit"
        ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

        try:
            return unicode(ureg(src).to(dest))
        except pint.unit.DimensionalityError as e:
            return unicode(e)
        except Exception as e:
            return "Failed to convert your request: {}".format(e)

    @botcmd
    def dice(self, mess, args):
        """[dice count] [sides] - Rolls the dice. Defaults to one dice and six sides."""
        args = args.split()

        dice = 1
        sides = 6
        try:
            dice = int(args[0])
            sides = int(args[1])
        except ValueError:
            return "Please provide integer parameters"
        except IndexError:
            pass

        if not 1 <= dice <= 50:
            return "Please limit yourself to up to 50 dice"
        if not 1 <= sides <= 256:
            return "Please limit yourself to up to 256 sides per dice"

        return "{} dice with {} sides each: [{}]".format(
            dice, sides, "][".join(map(unicode, (random.randint(1, sides) for _ in xrange(dice))))
        )

    @botcmd
    def roll(self, mess, args):
        """Picks a random number between 1 and 100"""
        return unicode(random.randint(1, 100))

    @botcmd
    def flipcoin(self, mess, args):
        """Flips a coin"""
        return random.choice(("Heads!", "Tails!"))

    @botcmd
    def pickone(self, mess, args):
        """<option1> or <option2> [or <option3> ...] - Chooses an option"""
        args = [item.strip() for item in args.split(" or ")]

        if len(args) > 1:
            return random.choice(args)
        else:
            return "Please provide multiple options to choose from"

    @botcmd
    def uptime(self, mess, args):
        """Bot's current uptime"""
        return "/me has been running for {}".format(datetime.utcnow() - self.startup_time)

    @botcmd(hidden=True)
    @requires_admin
    def reload(self, mess, args):
        """Kills the bot's process. Restarts the process if run in a while true loop."""
        if not args:
            self.quit()
            return "afk shower"

    @botcmd(hidden=True)
    @requires_dir_chat
    @requires_admin
    def gitpull(self, mess, args):
        """Pulls the latest commit from the active remote/branch"""
        p = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=path.abspath(path.join(path.dirname(__file__), pardir)))
        out, err = p.communicate()
        return "{}\n{}".format(out, err).strip()
