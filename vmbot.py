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

import xml.etree.ElementTree as ET
import time
import re
import logging
import random
import requests
from functools import wraps
import errno
import os
import signal
import subprocess

from sympy.printing.pretty import pretty
from sympy.parsing.sympy_parser import parse_expr
import vmbot_config as vmc

from fun import Say, Chains
from faq import FAQ
from utils import CREST, Price, EveUtils


logger = logging.getLogger('jabberbot')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
logger.addHandler(ch)


class MUCJabberBot(JabberBot):
    ''' Add features in JabberBot to allow it to handle specific
    characteristics of multiple users chatroom (MUC). '''

    # Overriding JabberBot base class
    max_chat_chars = 2000
    PING_FREQUENCY = 60
    PING_TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        ''' Initialize variables. '''
        self.nick_dict = {}

        # Answer only direct messages or not?
        self.only_direct = kwargs.pop('only_direct', False)

        # Initialize JabberBot
        super(MUCJabberBot, self).__init__(*args, **kwargs)

        # Create a regex to check if a message is a direct message
        user, domain = str(self.jid).split('@')
        self.direct_message_re = re.compile('^{}(@{})?[^\w]? '.format(user, domain))

    def unknown_command(self, mess, cmd, args):
        # This should fix the bot replying to IMs (SOLODRAKBANSOLODRAKBANSOLODRAKBAN)
        return ''

    def get_uname_from_mess(self, mess):
        node = mess.getFrom().getNode()
        juid = self.nick_dict[node][self.get_sender_username(mess)]
        return juid.split('@')[0]

    def callback_presence(self, conn, presence):
        nick = presence.getFrom().getResource()
        node = presence.getFrom().getNode()
        jid = presence.getJid()
        if jid is not None:
            if node not in self.nick_dict:
                self.nick_dict[node] = {}
            self.nick_dict[node][nick] = jid
        return super(MUCJabberBot, self).callback_presence(conn, presence)

    def callback_message(self, conn, mess):
        ''' Changes the behaviour of the JabberBot in order to allow
        it to answer direct messages. This is used often when it is
        connected in MUCs (multiple users chatroom). '''

        # solodrakban protection
        # Change this to be limited to certain people if you want by
        # if self.get_sender_username(mess) == 'solodrakban":
        if mess.getType() != "groupchat":
            return

        if vmc.nickname == self.get_sender_username(mess):
            return

        message = mess.getBody()
        if not message:
            return

        if self.direct_message_re.match(message):
            mess.setBody(' '.join(message.split(' ', 1)[1:]))
            return super(MUCJabberBot, self).callback_message(conn, mess)
        elif not self.only_direct:
            return super(MUCJabberBot, self).callback_message(conn, mess)

    def longreply(self, mess, text, forcePM=False, receiver=None):
        # FIXME: this should be integrated into the default send,
        # forcepm should be part of botcmd
        server = vmc.username.split('@')[1]
        if receiver is None:
            receiver = self.get_uname_from_mess(mess)

        if len(text) > self.max_chat_chars or forcePM:
            self.send('{}@{}'.format(receiver, server), text)
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

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


class VMBot(MUCJabberBot, Say, Chains, FAQ, CREST, Price, EveUtils):
    # Lists for use in the various methods
    directors = [
        "jack_haydn",
        "thirteen_fish",
        "pimpin_yourhos",
        "johann_tollefson",
        "petyr_baelich",
        "ektony",
        "kairk_efraim",
        "lofac",
        "jons_squire"
    ]
    admins = ["jack_haydn", "thirteen_fish"]

    def __init__(self, *args, **kwargs):
        super(VMBot, self).__init__(*args, **kwargs)

    @botcmd
    def math(self, mess, args):
        '''<expr> - Evaluates expr mathematically.

        Force floating point numbers by doing 4.0/3 instead of 4/3'''

        @timeout(10, "Sorry, this query took too long to execute and I had to kill it off.")
        def do_math(args):
            return pretty(parse_expr(args), full_prec=False, use_unicode=True)

        try:
            reply = do_math(args)
            if '\n' in reply:
                reply = '\n' + reply

            reply = '<font face="monospace">{}</font>'.format(
                re.sub('[\n]', '</font><br/><font face="monospace">', reply)
            )
        except Exception as e:
            reply = str(e)

        # TODO: what is the actual bound?
        if len(reply) > 2 ** 15:
            reply = "I've evaluated your expression but it's too long to send with jabber"
        return reply

    @botcmd
    def rtd(self, mess, args):
        '''Like a box of chocolates, you never know what you're gonna get'''
        with open("emotes.txt", 'r') as emotes:
            remotes = emotes.read().split('\n')

        while not remotes.pop(0).startswith('[default]'):
            pass

        return random.choice(remotes).split()[-1]

    @botcmd
    def dice(self, mess, args):
        '''[dice count] [sides] - Roll the dice. Defaults to one dice and six sides.'''
        dice = 1
        sides = 6
        args = args.strip().split()
        if len(args) > 2:
                return 'You need to provide none, one or two parameters.'

        try:
            dice = int(args[0])
            sides = int(args[1])
        except ValueError:
            return 'You need to provide integer parameters.'
        except IndexError:
            pass

        if not 0 <= dice <= 50:
            return "That's an absurd number of dice, try again"
        if not 1 <= sides <= 2**8:
            return "That's an absurd number of sides, try again"

        result = [random.randint(1, sides) for i in xrange(dice)]
        return 'I rolled {} dice with {} sides each. The result is [{}]'.format(
            dice, sides, ']['.join(map(str, result)))

    @botcmd
    def flipcoin(self, mess, args):
        '''flips a coin'''
        return random.choice(["Heads!", "Tails!"])

    @botcmd
    def pickone(self, mess, args):
        '''<option1> or <option2> [or <option3> ...] - Chooses an option for you'''
        args = args.strip().split(' or ')
        if len(args) > 1:
            return random.choice(args)
        else:
            return 'You need to provide at least 2 options to choose from.'

    @botcmd
    def ping(self, mess, args):
        '''[-a] - Is this thing on? The -a flag makes the bot answer to you specifically.'''
        if args == "-a":
            return '{}: Pong.'.format(self.get_sender_username(mess))
        else:
            return 'Pong.'

    def sendBcast(self, broadcast, author):
        result = ''
        messaging = ET.Element("messaging")
        messages = ET.SubElement(messaging, "messages")
        message = ET.SubElement(messages, "message")
        id = ET.SubElement(message, "id")
        id.text = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        target = ET.SubElement(message, "target")
        target.text = vmc.target
        sender = ET.SubElement(message, "from")
        sender.text = author
        text = ET.SubElement(message, "text")
        text.text = broadcast
        result = '<?xml version="1.0"?>' + ET.tostring(messaging)

        headers = {"X-SourceID": vmc.id, "X-SharedKey": vmc.key}
        r = requests.post(url=vmc.url, data=result, headers=headers)
        return r.status_code

    @botcmd
    def bcast(self, mess, args):
        ''' vm <message> - Sends a message to XVMX members

        Must be <=1kb including the tag line.
        "vm" required to avoid accidental bcasts, only works in dir chat.
        Do not abuse this or Solo's wrath shall be upon you.'''
        # API docs: https://goo.gl/cTYPzg
        if args[:2] != 'vm' or len(args) <= 3:
            return None

        srjid = self.get_uname_from_mess(mess)

        if str(mess.getFrom()).split("@")[0] != 'vm_dir':
            return "Broadcasting is only enabled in director chat."

        if srjid not in self.directors:
            return "You don't have the rights to send broadcasts."

        broadcast = args[3:]

        if len(broadcast) > 10240:
            return ("This broadcast has {} characters and is too long; "
                    "max length is 10240 characters. "
                    "Please try again with less of a tale. "
                    "You could try, y'know, a forum post.").format(len(broadcast))

        status = self.sendBcast(broadcast, "{} via VMBot".format(srjid))
        if status == 200:
            reply = "{}, I have sent your broadcast to {}".format(
                self.get_sender_username(mess), vmc.target)
        else:
            reply = ("{}, I failed to send your broadcast to {}"
                     " (Server returned error code <i>{}</i>)").format(
                        self.get_sender_username(mess), vmc.target, status)

        return reply

    @botcmd(hidden=True)
    def reload(self, mess, args):
        '''reload - Kills the bot's process

        If ran in a while true loop on the shell, it'll immediately reconnect.'''
        if not args:
            if self.get_uname_from_mess(mess) in self.admins:
                reply = 'afk shower'
                self.quit()
            else:
                reply = 'You are not authorized to reload the bot, please go and DIAF!'
            return reply

    @botcmd(hidden=True)
    def gitpull(self, mess, args):
        '''gitpull - pulls the latest commit from the bot repository and updates the bot with it.'''
        srjid = self.get_uname_from_mess(mess)
        if str(mess.getFrom()).split("@")[0] != 'vm_dir':
            return "git pull is only enabled in director chat."

        if srjid not in self.admins:
            return "You don't have the rights to git pull."

        p = subprocess.Popen(['git', 'pull', ],
                             cwd=r'/home/sjuengling/vmbot/',
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        reply = ('\n').join([out, err]).strip()

        return reply


if __name__ == '__main__':
    # Grabbing values from imported config file
    morgooglie = VMBot(vmc.username, vmc.password, vmc.res, only_direct=False)
    morgooglie.join_room(vmc.chatroom1, vmc.nickname)
    morgooglie.join_room(vmc.chatroom2, vmc.nickname)
    morgooglie.join_room(vmc.chatroom3, vmc.nickname)
    morgooglie.serve_forever()
