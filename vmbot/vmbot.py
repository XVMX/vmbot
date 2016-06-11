# coding: utf-8

import time
from datetime import datetime
import os
import subprocess
import random
import re
import xml.etree.ElementTree as ET

from xmpp.protocol import JID
from .jabberbot import JabberBot
import requests
from sympy.parsing.sympy_parser import parse_expr
from sympy.printing.pretty import pretty
import pint

from .botcmd import botcmd
from .config import config
from .fun import Say, Fun, Chains
from .utils import Price, EVEUtils
from .wh import Wormhole
from .helpers.decorators import timeout
from .helpers.regex import ZKB_REGEX


class MUCJabberBot(JabberBot):
    """Add features in JabberBot to allow it to handle specific characteristics of MUCs."""

    # Overriding JabberBot base class
    MAX_CHAT_CHARS = 800
    PING_FREQUENCY = 60
    PING_TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        self.nick_dict = {}
        super(MUCJabberBot, self).__init__(*args, **kwargs)

    def get_uname_from_mess(self, mess, full_jid=False):
        nick = self.get_sender_username(mess)
        node = mess.getFrom().getNode()

        if nick == node:
            return nick

        jid = self.nick_dict[node].get(nick, JID("default"))
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


class VMBot(MUCJabberBot, Say, Fun, Chains, Price, EVEUtils, Wormhole):
    # Access control lists
    DIRECTORS = (
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
    )
    ADMINS = (
        "joker_gates",
    )

    # Pubbie talk regex parts
    PUBBIETALK = (
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
    )

    def __init__(self, *args, **kwargs):
        self.startup_time = datetime.now()
        self.km_feed_trigger = time.time() if kwargs.pop('km_feed', False) else None
        self.news_feed_trigger = time.time() if kwargs.pop('news_feed', False) else None

        super(VMBot, self).__init__(*args, **kwargs)

        # Regex to check for pubbie talk
        self.pubbie_regex = re.compile("(?:^|\s)(?:{})(?:$|\s)".format('|'.join(self.PUBBIETALK)),
                                       re.IGNORECASE)
        self.pubbie_kicked = set()

        # Initialize asynchronous commands
        if self.km_feed_trigger:
            try:
                self.km_feed_id = requests.get(
                    "https://zkillboard.com/api/losses/corporationID/2052404106/"
                    "limit/1/no-items/no-attackers/",
                    headers={'User-Agent': "XVMX JabberBot"}, timeout=3
                ).json()[0]['killID']
            except (requests.exceptions.RequestException, ValueError):
                self.km_feed_trigger = None

        if self.news_feed_trigger:
            self.news_feed_ids = {'news': None, 'devblog': None}

    def idle_proc(self):
        """Execute asynchronous commands."""
        if self.km_feed_trigger and self.km_feed_trigger <= time.time():
            self.km_feed()
            self.km_feed_trigger += 5 * 60

        if self.news_feed_trigger and self.news_feed_trigger <= time.time():
            self.news_feed()
            self.news_feed_trigger += 60 * 60

        return super(VMBot, self).idle_proc()

    def callback_presence(self, conn, presence):
        reply = super(VMBot, self).callback_presence(conn, presence)

        jid = presence.getJid()
        if jid is None:
            return reply

        type_ = presence.getType()
        jid = JID(jid).getStripped()

        if type_ == self.AVAILABLE:
            nick = presence.getFrom().getResource()
            room = presence.getFrom().getStripped()

            if jid in self.pubbie_kicked and room == config['jabber']['chatrooms'][0]:
                self.send(config['jabber']['chatrooms'][0],
                          "{}: Talk shit, get hit".format(nick),
                          message_type="groupchat")
                self.pubbie_kicked.remove(jid)
        elif type_ == self.OFFLINE and presence.getStatusCode() == "307":
            self.pubbie_kicked.add(jid)

        return reply

    def callback_message(self, conn, mess):
        reply = super(VMBot, self).callback_message(conn, mess)

        # See XEP-0203: Delayed Delivery (http://xmpp.org/extensions/xep-0203.html)
        if "urn:xmpp:delay" in mess.getProperties():
            return reply

        message = mess.getBody()
        room = mess.getFrom().getStripped()
        primary_room = room == config['jabber']['chatrooms'][0]

        if message and self.get_uname_from_mess(mess, full_jid=True) != self.jid:
            if self.pubbie_regex.search(message) is not None and primary_room:
                self.muc_kick(room, self.get_sender_username(mess),
                              "Emergency pubbie broadcast system")

            if not message.lower().startswith("zbot"):
                matches = {match.group(0) for match in ZKB_REGEX.finditer(message)}
                replies = [self.zbot(mess, match, compact=True) for match in matches]
                if replies:
                    self.send_simple_reply(mess, "<br />".join(replies))

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

        return reply

    @botcmd
    def convert(self, mess, args):
        """<amount> <source> to <destination> - Converts amount from source to destination"""
        src, dest = args.split(" to ", 1)
        ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

        try:
            return str(ureg(src).to(dest))
        except pint.unit.DimensionalityError as e:
            return str(e)
        except Exception as e:
            return "Failed to convert your request: {}".format(e)

    @botcmd
    def dice(self, mess, args):
        """[dice count] [sides] - Roll the dice. Defaults to one dice and six sides"""
        args = args.split()
        if len(args) > 2:
            return "You need to provide none, one or two parameters"

        dice = 1
        sides = 6
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
            dice, sides, "][".join(map(str, (random.randint(1, sides) for i in xrange(dice))))
        )

    @botcmd
    def roll(self, mess, args):
        """Displays a random number between 1 and 100"""
        return str(random.randint(1, 100))

    @botcmd
    def flipcoin(self, mess, args):
        """Flips a coin"""
        return random.choice(("Heads!", "Tails!"))

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

        def send_bcast(broadcast, author):
            # API docs: http://goo.gl/cTYPzg
            messaging = ET.Element("messaging")
            messages = ET.SubElement(messaging, "messages")
            message = ET.SubElement(messages, "message")
            id_ = ET.SubElement(message, "id")
            id_.text = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            target = ET.SubElement(message, "target")
            target.text = config['bcast']['target']
            sender = ET.SubElement(message, "from")
            sender.text = author
            text = ET.SubElement(message, "text")
            text.text = broadcast
            result = '<?xml version="1.0"?>' + ET.tostring(messaging)

            try:
                r = requests.post(
                    config['bcast']['url'], data=result,
                    headers={'User-Agent': "XVMX JabberBot",
                             'X-SourceID': config['bcast']['id'],
                             'X-SharedKey': config['bcast']['key']},
                    timeout=10
                )
                return r.status_code
            except requests.exceptions.RequestException as e:
                return str(e)

        if not args.startswith("vm "):
            return None
        broadcast = args[3:]

        if mess.getFrom().getNode() != "vm_dir":
            return "Broadcasting is only enabled in director chat"

        sender = self.get_uname_from_mess(mess)
        if sender not in self.DIRECTORS:
            return "You don't have the rights to send broadcasts"

        if len(broadcast) > 10240:
            return ("This broadcast has {} characters and is too long; "
                    "max length is 10240 characters. Please try again with less of a tale. "
                    "You could try, y'know, a forum post.").format(len(broadcast))

        status = send_bcast(broadcast, "{} via VMBot".format(sender))
        if status == 200:
            return "{}, I have sent your broadcast to {}".format(self.get_sender_username(mess),
                                                                 config['bcast']['target'])
        elif isinstance(status, str):
            return "Error while connecting to Broadcast-API: {}".format(status)
        else:
            return "Broadcast-API returned error code {}".format(status)

    @botcmd
    def pingall(self, mess, args):
        """Pings everyone in the current MUC room"""
        if self.get_uname_from_mess(mess) not in self.DIRECTORS:
            return ":getout:"

        reply = "All hands on {} dick!\n".format(self.get_sender_username(mess))
        reply += ", ".join(self.nick_dict[mess.getFrom().getNode()].keys())
        return reply

    @botcmd
    def uptime(self, mess, args):
        """Displays for how long the bot is running already"""
        return "arc_codie has servers, but they haven't been up as long as {}".format(
            datetime.now() - self.startup_time
        )

    @botcmd(hidden=True)
    def reload(self, mess, args):
        """Kills the bot's process

        If ran in a while true loop on the shell, it'll immediately reconnect.
        """
        if not args:
            if self.get_uname_from_mess(mess) in self.ADMINS:
                self.quit()
                return "afk shower"
            else:
                return "You are not authorized to reload the bot, please go and DIAF!"

    @botcmd(hidden=True)
    def gitpull(self, mess, args):
        """Pulls the latest commit from the bot repository and updates the bot with it"""
        if mess.getFrom().getNode() != "vm_dir":
            return "git pull is only enabled in director chat"

        if self.get_uname_from_mess(mess) not in self.ADMINS:
            return "You are not allowed to git pull"

        path = os.path
        p = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=path.abspath(path.join(path.dirname(__file__), os.pardir)))
        out, err = p.communicate()
        return "{}\n{}".format(out, err).strip()
