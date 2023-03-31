# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
from datetime import datetime
from collections import defaultdict
import signal
from os import path, pardir
import subprocess
import random

from concurrent import futures
from multiset import Multiset
from xmpp import NS_DELAY as XEP_0091_DELAY
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
from .helpers.sso import SSOToken
from .helpers.decorators import timeout, requires_role, inject_db
from .helpers.format import format_jid_nick
from .helpers.regex import PUBBIE_REGEX, ZKB_REGEX, YT_REGEX
from .models.message import Message
from .models.user import User, Nickname
from .models import Note

import config

# See XEP-0203: Delayed Delivery (https://xmpp.org/extensions/xep-0203.html)
XEP_0203_DELAY = b"urn:xmpp:delay"
DELAY_NS_SET = {XEP_0203_DELAY, XEP_0091_DELAY}


class MUCJabberBot(JabberBot):
    """Add features in JabberBot to allow it to handle specific characteristics of MUCs."""

    # Overriding JabberBot base class
    PING_FREQUENCY = 60
    PING_TIMEOUT = 5

    MAX_CHAT_CHARS = 2000
    MAX_CHAT_LINES = 10

    def __init__(self, username, password, res, *args, **kwargs):
        super(MUCJabberBot, self).__init__(username, password, res, *args, **kwargs)
        self.jid.setResource(res)
        self.occupant_jids = Multiset()
        self.nick_dict = defaultdict(dict)

    def get_sender_username(self, mess):
        from_ = mess.getFrom()

        # In MUCs and MUC PMs, the from attribute contains the sender's MUC address
        if mess.getType() == b"groupchat" or from_.getStripped() in config.JABBER['chatrooms']:
            return from_.getResource()
        else:
            return from_.getNode()

    def get_uname_from_mess(self, mess, full_jid=False):
        from_ = mess.getFrom()

        # In MUCs and MUC PMs, the from attribute contains the sender's MUC address
        if mess.getType() == b"groupchat" or from_.getStripped() in config.JABBER['chatrooms']:
            room, nick = from_.getNode(), from_.getResource()
            try:
                from_ = self.nick_dict[room][nick]
            except KeyError:
                from_ = JID(b"default")

        return from_ if full_jid else from_.getNode()

    def build_reply(self, mess, text=None, private=False):
        res = super(MUCJabberBot, self).build_reply(mess, text=text, private=private)
        if mess.getType() == b"chat":
            # Ensure response is sent to correct resource for (MUC) PMs
            res.setTo(mess.getFrom())

        return res

    def callback_presence(self, conn, presence):
        room = presence.getFrom().getNode()
        nick = presence.getFrom().getResource()
        jid = presence.getJid()

        if jid is not None:
            # JID attribute is only included in MUC presence stanzas
            jid = JID(jid)
            if presence.getType() == self.OFFLINE:
                self.nick_dict[room].pop(nick, None)
                self.occupant_jids[jid] -= 1
            else:
                self.occupant_jids[jid] += 1
                self.nick_dict[room][nick] = jid

        return super(MUCJabberBot, self).callback_presence(conn, presence)

    def should_ignore_message(self, mess):
        # solodrakban (PM) protection
        # Discard PMs unless they are sent via a MUC or from a known MUC occupant
        type_ = mess.getType()
        if type_ == b"chat":
            sender = mess.getFrom()
            stripped = sender.getStripped()
            if ((sender not in self.occupant_jids or stripped in config.JABBER['pm_blacklist'])
                    and stripped not in config.JABBER['chatrooms']):
                return True
        elif type_ != b"groupchat":
            return True

        # Discard delayed messages
        if any(prop in DELAY_NS_SET for prop in mess.getProperties()):
            return True

        # Discard messages from myself
        if self.get_uname_from_mess(mess, full_jid=True) == self.jid:
            return True

        return False

    def get_cmd_from_text(self, text):
        text = text.split(b' ', 1)
        cmd = text.pop(0).lower()
        args = text[0] if text else b""

        return self.commands.get(cmd, None), args

    def callback_message(self, conn, mess):
        if self.should_ignore_message(mess):
            return

        text = mess.getBody()
        if not text:
            return

        cmd, args = self.get_cmd_from_text(text)
        if cmd is None:
            return

        try:
            reply = cmd(mess, args)
        except Exception:
            self.log.exception('An error happened while processing a message ("%s") from %s:',
                               text, mess.getFrom())
            reply = self.MSG_ERROR_OCCURRED

        if reply:
            lines = reply.count('\n') + reply.count("<br/>") + reply.count("<br />")
            if (len(reply) > self.MAX_CHAT_CHARS or lines > self.MAX_CHAT_LINES
                    or cmd._vmbot_forcepm) and mess.getType() == b"groupchat":
                self.send_simple_reply(mess, reply, private=True)
                reply = "Private message sent"

            self.send_simple_reply(mess, reply)

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
        cmd, args = self.get_cmd_from_text(args.lstrip())
        if cmd is not None:
            self.send_simple_reply(mess, cmd(mess, args))


class VMBot(ACL, Director, Say, Fun, Chains, Pager, Price, EVEUtils, MUCJabberBot):
    """Aggregate base commands and mixins into a combined bot."""

    MESSAGE_INTERVAL = 60

    def __init__(self, *args, **kwargs):
        self.startup_time = datetime.utcnow()
        super(VMBot, self).__init__(*args, **kwargs)

        self.message_trigger = time.time() + 30
        self.sess = db.Session()

        self.api_pool = futures.ThreadPoolExecutor(max_workers=20)
        self.yt_quota_exceeded = False
        if config.ZKILL_FEED:
            self.km_feed = KMFeed(config.CORPORATION_ID)

    def idle_proc(self):
        """Retrieve and send stored messages."""
        if self.message_trigger <= time.time():
            if config.ZKILL_FEED:
                for km_res in self.km_feed.process():
                    if not km_res:
                        continue
                    for room in config.JABBER['primary_chatrooms']:
                        self.send(user=room, text=km_res, message_type="groupchat")

            # Cron messages
            select_msg = db.select(Message).order_by(Message.message_id.asc())
            for mess in self.sess.execute(select_msg).scalars():
                self.send(**mess.send_dict)
                self.sess.delete(mess)

            # Notes
            for mess in self.pager_queue.fetch(self.nick_dict, self.sess):
                self.send(**mess.send_dict)

            self.sess.commit()
            self.message_trigger += self.MESSAGE_INTERVAL

        return super(VMBot, self).idle_proc()

    def callback_presence(self, conn, presence):
        jid = presence.getJid()
        nick_str = presence.getFrom().getResource()

        if jid is not None:
            jid = JID(jid).getStripped()
            nick = self.sess.get(Nickname, (nick_str, jid))

            if nick is None:
                nick = Nickname(nick_str)
                nick.user = (self.sess.get(User, jid, options=(db.joinedload(User.nicks),))
                             or User(jid))
                self.sess.add(nick)
            else:
                nick.last_seen = datetime.utcnow()

            self.sess.commit()

        return super(VMBot, self).callback_presence(conn, presence)

    def callback_message(self, conn, mess):
        reply = super(VMBot, self).callback_message(conn, mess)
        if self.should_ignore_message(mess):
            return reply

        msg = mess.getBody()
        room = mess.getFrom().getStripped()
        if msg:
            if (config.PUBBIE_SMACKTALK and PUBBIE_REGEX.search(msg) is not None
                    and room in config.JABBER['primary_chatrooms']):
                self.send_simple_reply(mess, self.pubbiesmack(mess))

            # zBot
            if config.ZBOT:
                matches = {match.group(1) for match in ZKB_REGEX.finditer(msg)}
                replies = [api.zbot(match) for match in matches]
                if replies:
                    self.send_simple_reply(mess, '\n'.join(replies))

            # YTBot
            if not self.yt_quota_exceeded:
                matches = {match.group(1) for match in YT_REGEX.finditer(msg)}
                replies = []
                for match in matches:
                    reply = api.ytbot(match)
                    if reply is None:
                        continue
                    if reply is False:
                        self.yt_quota_exceeded = True
                        break
                    replies.append(reply)

                if replies:
                    self.send_simple_reply(mess, '\n'.join(replies))

        return reply

    def shutdown(self):
        nicks = {(nick, jid.getStripped()) for room in self.nick_dict.values()
                 for nick, jid in room.items()}
        update_nicks = (db.update(Nickname).where(Nickname.nick == db.bindparam("n"),
                                                  Nickname._user_jid == db.bindparam("j")).
                        values(last_seen=datetime.utcnow()).
                        execution_options(synchronize_session=False))
        try:
            self.sess.execute(update_nicks, [{"n": nick, "j": jid} for nick, jid in nicks])
            self.sess.commit()
        except db.OperationalError:
            self.sess.rollback()

        self.sess.close()
        if config.ZKILL_FEED:
            self.km_feed.close()

        return super(VMBot, self).shutdown()

    def get_token(self):
        try:
            return self._token
        except AttributeError:
            self._token = SSOToken.from_refresh_token(config.SSO['refresh_token'])
            return self._token

    @staticmethod
    @timeout(5, "Your calculation is too expensive and was not completed")
    def _do_math(args):
        return pretty(parse_expr(args), full_prec=False, use_unicode=True)

    @botcmd(disable_if=not hasattr(signal, "alarm"))
    def math(self, mess, args):
        """<expr> - Evaluates expr mathematically"""
        try:
            reply = self._do_math(args)
        except TimeoutError as e:
            return unicode(e)
        except Exception:
            return  # probably an unintended invocation

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
            return  # probably an unintended invocation
        ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

        try:
            res = ureg(src, case_sensitive=False).to(ureg(dest, case_sensitive=False))
            return "{:.6g}".format(res)
        except (pint.UndefinedUnitError, pint.DimensionalityError) as e:
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
            return  # probably an unintended invocation
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
        jid = args + "@%" if '@' not in args else args

        select_usrs = db.select(
            User.jid, db.null().label("nick"),
            db.func.max(Nickname.last_seen).label("last_seen")
        ).join(Nickname).where(User.jid.ilike(jid)).group_by(User.jid)
        select_nicks = db.select(
            Nickname._user_jid.label("jid"), Nickname.nick, Nickname.last_seen
        ).where(Nickname.nick.ilike(args), ~Nickname._user_jid.ilike(jid))

        seen = session.execute(select_usrs.union_all(select_nicks)).all()
        if not seen:
            return "I've never seen that user before"

        if len(seen) == 1:
            jid, nick, last_seen = seen[0]
            return ("The last time I've seen {} was at {:%Y-%m-%d %H:%M:%S}"
                    .format(format_jid_nick(jid, nick), last_seen))

        res = ["I've seen the following people use that name:"]
        res.extend("{} at {:%Y-%m-%d %H:%M:%S}".format(format_jid_nick(jid, nick), last_seen)
                   for jid, nick, last_seen in seen)
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

    @botcmd(hidden=True, force_pm=True)
    @requires_role("admin")
    def gitpull(self, mess, args):
        """Pulls the latest commit from the active remote/branch"""
        p = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=path.abspath(path.join(path.dirname(__file__), pardir)))
        out, err = p.communicate()
        return "{}\n{}".format(out, err).strip()
