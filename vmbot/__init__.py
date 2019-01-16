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
from .acl import ACL
from .director import Director
from .fun import Say, Fun, Chains
from .pager import Pager
from .price import Price
from .utils import EVEUtils
from .async.km_feed import KMFeed
from .helpers.exceptions import TimeoutError
from .helpers import database as db
from .helpers import api
from .helpers.decorators import timeout, requires_role, requires_dir_chat, inject_db
from .helpers.regex import PUBBIE_REGEX, ZKB_REGEX
from .models.message import Message
from .models.user import User, Nickname
from .models import Note

import config

# See XEP-0203: Delayed Delivery (https://xmpp.org/extensions/xep-0203.html)
XEP_0203_DELAY = "urn:xmpp:delay"
MESSAGE_INTERVAL = 60


class MUCJabberBot(JabberBot):
    """Add features in JabberBot to allow it to handle specific characteristics of MUCs."""

    # Overriding JabberBot base class
    MAX_CHAT_CHARS = 2000
    MAX_CHAT_LINES = 10
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

        lines = text.count('\n') + text.count("<br/>") + text.count("<br />")
        if (len(text) > self.MAX_CHAT_CHARS or lines > self.MAX_CHAT_LINES or
                getattr(cmd, "_vmbot_forcepm", False)):
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

        if XEP_0203_DELAY in mess.getProperties():
            return

        # Discard messages from myself
        if self.get_uname_from_mess(mess, full_jid=True) == self.jid:
            return

        return super(MUCJabberBot, self).callback_message(conn, mess)

    @botcmd
    def help(self, mess, args):
        reply = super(MUCJabberBot, self).help(mess, args)
        if not args or not reply:
            return reply

        # Fix multiline docstring indentation (see PEP 257)
        lines = reply.splitlines()
        try:
            minindent = min(len(line) - len(line.lstrip()) for line in lines[1:] if line.lstrip())
        except ValueError:
            minindent = 0

        fixed = [lines[0].strip()]
        for line in lines[1:]:
            fixed.append(line[minindent:].rstrip())
        while fixed and not fixed[0]:
            fixed.pop(0)
        while fixed and not fixed[-1]:
            fixed.pop()

        return '\n'.join(fixed)

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


class VMBot(MUCJabberBot, ACL, Director, Say, Fun, Chains, Pager, Price, EVEUtils):
    def __init__(self, *args, **kwargs):
        self.startup_time = datetime.utcnow()
        self.message_trigger = None
        self.sess = db.Session()

        if kwargs.pop('feeds', False):
            self.message_trigger = time.time() + 30
            self.km_feed = KMFeed(config.CORPORATION_ID)

        super(VMBot, self).__init__(*args, **kwargs)

    def idle_proc(self):
        """Retrieve and send stored messages."""
        if self.message_trigger and self.message_trigger <= time.time():
            # KM feed
            for km_res in (res for res in self.km_feed.process() if res):
                for room in config.JABBER['primary_chatrooms']:
                    self.send(user=room, text=km_res, message_type="groupchat")

            # Cron messages
            for mess in self.sess.query(Message).order_by(Message.message_id.asc()).all():
                self.send(**mess.send_dict)
                self.sess.delete(mess)

            # Notes
            for mess in Note.process_notes(self.nick_dict, self.sess):
                self.send(**mess.send_dict)

            self.sess.commit()
            self.message_trigger += MESSAGE_INTERVAL

        return super(VMBot, self).idle_proc()

    def callback_presence(self, conn, presence):
        jid = presence.getJid()
        nick_str = presence.getFrom().getResource()

        if jid is not None:
            jid = JID(jid).getStripped()
            usr = self.sess.query(User).get(jid) or User(jid)
            nick = self.sess.query(Nickname).get((nick_str, usr.jid))

            if nick is None:
                usr.nicks.append(Nickname(nick_str))
            else:
                nick.last_seen = datetime.utcnow()

            self.sess.add(usr)
            self.sess.commit()

        return super(VMBot, self).callback_presence(conn, presence)

    def callback_message(self, conn, mess):
        reply = super(VMBot, self).callback_message(conn, mess)

        if (self.get_uname_from_mess(mess, full_jid=True) == self.jid or
                mess.getType() != "groupchat" or XEP_0203_DELAY in mess.getProperties()):
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

    def shutdown(self):
        nicks = {(nick, jid.getStripped()) for node in self.nick_dict.values()
                 for nick, jid in node.items()}
        try:
            self.sess.query(Nickname).filter(db.or_(
                False,  # Prevents matching everything if nicks is empty
                *(db.and_(Nickname.nick == nick, Nickname._user_jid == jid) for nick, jid in nicks)
            )).update({'last_seen': datetime.utcnow()}, synchronize_session=False)
            self.sess.commit()
        except db.OperationalError:
            pass

        self.sess.close()
        if self.message_trigger:
            self.km_feed.close()

        return super(VMBot, self).shutdown()

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
        except pint.DimensionalityError as e:
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
    @inject_db
    def lastseen(self, mess, args, session):
        """<user> - Looks up the last time user was seen by the bot"""
        if not args:
            return

        # Join prevents users without associated nickname(s) from being selected
        usrs = session.query(User).join(User.nicks).filter(User.jid.ilike(args + "@%")).all()
        nicks = session.query(Nickname).filter(Nickname.nick.ilike(args),
                                               Nickname._user_jid.notin_(u.jid for u in usrs)).all()

        if not usrs and not nicks:
            return "I've never seen that user before"

        if len(usrs) + len(nicks) == 1:
            if usrs:
                return "The last time I've seen {} was at {:%Y-%m-%d %H:%M:%S}".format(
                    usrs[0].uname, usrs[0].last_seen
                )
            else:
                return "The last time I've seen {} ({}) was at {:%Y-%m-%d %H:%M:%S}".format(
                    nicks[0].nick, nicks[0].user.uname, nicks[0].last_seen
                )

        res = ["I've seen the following people use that name:"]
        res.extend("{} at {:%Y-%m-%d %H:%M:%S}".format(usr.uname, usr.last_seen) for usr in usrs)
        res.extend("{} ({}) at {:%Y-%m-%d %H:%M:%S}".format(nick.nick, nick.user.uname,
                                                            nick.last_seen) for nick in nicks)
        return '\n'.join(res)

    @botcmd
    def uptime(self, mess, args):
        """Bot's current uptime and git revision"""
        p = subprocess.Popen(["git", "rev-parse", "--short", "HEAD"], stdout=subprocess.PIPE,
                             cwd=path.abspath(path.join(path.dirname(__file__), pardir)))
        out, _ = p.communicate()

        res = "/me has been running for {}".format(datetime.utcnow() - self.startup_time)
        if p.returncode == 0:
            res += (" (<em>Revision "
                    '<a href="https://github.com/XVMX/vmbot/tree/{0}">{0}</a></em>)'.format(out))

        return res

    @botcmd(hidden=True)
    @requires_role("admin")
    def reload(self, mess, args):
        """Kills the bot's process. Restarts the process if run in a while true loop."""
        if not args:
            self.quit()
            return "afk shower"

    @botcmd(hidden=True)
    @requires_dir_chat
    @requires_role("admin")
    def gitpull(self, mess, args):
        """Pulls the latest commit from the active remote/branch"""
        p = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=path.abspath(path.join(path.dirname(__file__), pardir)))
        out, err = p.communicate()
        return "{}\n{}".format(out, err).strip()
