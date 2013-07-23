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
from datetime import datetime, timedelta
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

from sympy.parsing.sympy_parser import parse_expr
import vmbot_config as vmc

logger = logging.getLogger('jabberbot')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
logger.addHandler(ch)

class MUCJabberBot(JabberBot):

    ''' Add features in JabberBot to allow it to handle specific
    caractheristics of multiple users chatroom (MUC). '''

    def __init__(self, *args, **kwargs):
        ''' Initialize variables. '''

        # answer only direct messages or not?
        self.only_direct = kwargs.pop('only_direct', False)

        # initialize jabberbot
        super(MUCJabberBot, self).__init__(*args, **kwargs)

        # create a regex to check if a message is a direct message
        user, domain = str(self.jid).split('@')
        self.direct_message_re = re.compile('^%s(@%s)?[^\w]? ' \
                % (user, domain))

    def callback_message(self, conn, mess):
        ''' Changes the behaviour of the JabberBot in order to allow
        it to answer direct messages. This is used often when it is
        connected in MUCs (multiple users chatroom). '''

        message = mess.getBody()
        if not message:
            return

        if self.direct_message_re.match(message):
            mess.setBody(' '.join(message.split(' ', 1)[1:]))
            return super(MUCJabberBot, self).callback_message(conn, mess)
        elif not self.only_direct:
            return super(MUCJabberBot, self).callback_message(conn, mess)

class VMBotError(StandardError):
    def __init__(self, msg):
        super(VMBotError, self).__init__(msg)

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

class VMBot(MUCJabberBot):
    # Lists for use in the various methods
    eball_answers = ['Probably.', 'Rather likely.', 'Definitely.', 'Of course.', 'Probably not.', 'This is very questionable.', 'Unlikely.', 'Absolutely not.']
    fishisms = ["~The Python Way!~", "HOOOOOOOOOOOOOOOOOOOOOOO! SWISH!", "DIVERGENT ZONES!", "BONUSSCHWEIN! BONUSSCHWEIN!"]
    pimpisms = ["eabod"]
    directors = ["jack_haydn", "thirteen_fish", "pimpin_yourhos", "petter_sandstad", "johann_tollefson", "petyr_baelich", "arele", "kairk_efraim"]

    def __init__(self, *args, **kwargs):
        # initialize jabberbot
        super(VMBot, self).__init__(*args, **kwargs)

    @timeout(10, "Sorry, this query took too long to execute and I had to kill it off.")
    def do_math(self, args):
        return str(parse_expr(args))

    @botcmd
    def math(self, mess, args):
        '''math <expr> - Evaluates expr mathematically. If you want decimal results, force floating point numbers by doing 4.0/3 instead of 4/3'''

        try:
            reply = self.do_math(args)
        except Exception, e:
            reply = str(e)

        if len(reply) > 2 ** 15:  # TODO: what is the actual bound?
            reply = "I've evaluated your expression but it's too long to send with jabber"
        self.send_simple_reply(mess, reply)

    @botcmd
    def bot_8ball(self, mess, args):
        '''8ball <question> - Provides insight into the future'''
        if len(args) == 0:
            reply = 'You will need to provide a question for me to answer.'
        else:
            reply = random.choice(self.eball_answers)
        self.send_simple_reply(mess, reply)

    @botcmd
    def evetime(self, mess, args):
        '''evetime [+offset] - Displays the current evetime and the resulting evetime of the offset, if provided'''
        timefmt = '%Y-%m-%d %H:%M:%S'
        evetime = datetime.utcnow()
        reply = 'The current EVE time is ' + evetime.strftime(timefmt)
        try:
            offset_time = timedelta(hours=int(args)) + evetime
            reply += ' and {} hour(s) is {}'.format(args.strip(), offset_time.strftime(timefmt))
        except ValueError:
            pass
        self.send_simple_reply(mess, reply)

    @botcmd
    def sayhi(self, mess, args):
        '''sayhi - Says hi to you!'''
        reply = "Hi " + self.get_sender_username(mess) + "!"
        self.send_simple_reply(mess, reply)

    @botcmd(hidden=True)
    def every(self, mess, args):
        '''Every lion except for at most one'''
        if len(args) < 6 and random.randint(1, 6) == 1:
            reply = "lion"
            self.send_simple_reply(mess, reply)

    @botcmd(hidden=True)
    def lion(self, mess, args):
        '''Every lion except for at most one'''
        if len(args) < 5 and random.randint(1, 6) == 1:
            reply = "except"
            self.send_simple_reply(mess, reply)

    @botcmd(hidden=True)
    def bot_except(self, mess, args):
        '''Every lion except for at most one'''
        if len(args) < 7 and random.randint(1, 6) == 1:
            reply = "for"
            self.send_simple_reply(mess, reply)

    @botcmd(hidden=True)
    def bot_for(self, mess, args):
        '''Every lion except for at most one'''
        if len(args) < 4 and random.randint(1, 6) == 1:
            reply = "at"
            self.send_simple_reply(mess, reply)

    @botcmd(hidden=True)
    def at(self, mess, args):
        '''Every lion except for at most one'''
        if len(args) < 3 and random.randint(1, 6) == 1:
            reply = "most"
            self.send_simple_reply(mess, reply)

    @botcmd(hidden=True)
    def bot_most(self, mess, args):
        '''Every lion except for at most one'''
        if len(args) < 5 and random.randint(1, 6) == 1:
            reply = "one"
            self.send_simple_reply(mess, reply)

    @botcmd(hidden=True)
    def bot_one(self, mess, args):
        '''Every lion except for at most one'''
        if len(args) < 4 and random.randint(1, 6) == 1:
            reply = ":bravo:"
            self.send_simple_reply(mess, reply)

    @botcmd
    def fishsay(self, mess, args):
        '''fishsay - fishy wisdom.'''
        self.send_simple_reply(mess, random.choice(self.fishisms))

    @botcmd
    def pimpsay(self, mess, args):
        self.send_simple_reply(mess, random.choice(self.pimpisms))

    @botcmd
    def rtd(self, mess, args):
        '''rtd [dice count] [sides] - Roll the dice. If no dice count/sides are provided, one dice and six sides will be assumed.'''
        dice = 1
        sides = 6
        # TODO: still kind of messy, need to take a second pass at this
        try:
            if args:
                args = args.strip().split(' ')
                if len(args) > 2:
                    raise VMBotError('You need to provide none, one or two parameters.')

                try:
                    dice = int(args[0])
                    sides = int(args[1])
                except ValueError:
                    raise VMBotError('You need to provide integer parameters.')
                except IndexError:
                    pass

                if dice not in xrange(1000) or sides not in xrange(1, 1000):
                    raise VMBotError("I want to see those dice/seeing you throw that many dice, dude. I don't get paid, so find someone else to do that for you, tyvm.")

            result = ''
            for i in range(dice):
                result += str([random.randint(1, sides)])
            reply = 'I rolled {} dice with {} sides each. The result is {}'.format(dice, sides, result)
        except VMBotError, e:
            reply = str(e)
        finally:
            self.send_simple_reply(mess, reply)

    @botcmd
    def flipcoin(self, mess, args):
        '''flipcoin - flips a coin'''
        self.send_simple_reply(mess, random.choice(["Heads!", "Tails!"]))

    @botcmd
    def bcast(self, mess, args):
        '''bcast vm <message> - Sends a message to XVMX members. Must be <=1kb including the tag line. "vm" required to avoid accidental bcasts, only works in dir chat. Do not abuse this or Solo's wrath shall be upon you.
        A hacked together piece of shit.
        API docs: https://goonfleet.com/index.php?/topic/178259-announcing-the-gsf-web-broadcast-system-and-broadcast-rest-like-api/
        '''

        srjid = self.senderRjid(mess)

        if args[:2] != 'vm' or len(args) <= 3:
            return

        try:
            if str(mess.getFrom()).split("@")[0] != 'vm_dir':
                raise VMBotError("Broadcasting is only enabled in director chat.")

            if srjid not in self.directors:
                raise VMBotError("You don't have the rights to send broadcasts.")

            footer = '\n\n *** This was a broadcast by {} to {} through VMBot at {} EVE. ***'.format(srjid, vmc.target, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()))
            broadcast = args[3:] + footer

            if len(broadcast) > 1024:
                raise VMBotError("This broadcast is too long; max length is 1024 characters including the automatically generated info line at the end. Please try again with less of a tale.")

            self.sendBcast(broadcast)
            reply = self.get_sender_username(mess) + ", I have sent your broadcast to " + vmc.target
        except VMBotError, e:
            reply = str(e)
        finally:
            self.send_simple_reply(mess, reply)

    @botcmd
    def pickone(self, mess, args):
        '''pickone <option1> or <option2> [or <option3> ...] - Chooses an option for you'''
        args = args.strip().split(' or ')
        if len(args) > 1:
            reply = random.choice(args)
        else:
            reply = 'You need to provide at least 2 options to choose from.'

        self.send_simple_reply(mess, reply)

    @botcmd
    def ping(self, mess, args):
        '''ping [-a] - Is this thing on? The -a flag makes the bot answer to you specifically.'''
        if args == "-a":
            reply = self.get_sender_username(mess) + ': Pong.'
        else:
            reply = 'Pong.'
        self.send_simple_reply(mess, reply)

    @botcmd(hidden=True)
    def reload(self, mess, args):
        if len(args) == 0:
            if self.senderRjid(mess) == 'jack_haydn' and self.get_sender_username(mess) != vmc.nickname:
                reply = 'afk shower'
                self.quit()
            else:
                reply = 'You are not authorized to reload the bot, please go and DIAF!'

            self.send_simple_reply(mess, reply)

    def sendBcast(self, broadcast):
        result = ''
        messaging = ET.Element("messaging")
        messages = ET.SubElement(messaging, "messages")
        message = ET.SubElement(messages, "message")
        id = ET.SubElement(message, "id")
        id.text = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        target = ET.SubElement(message, "target")
        target.text = vmc.target
        text = ET.SubElement(message, "text")
        text.text = broadcast
        result = '<?xml version="1.0"?>' + ET.tostring(messaging)
        # print result

        headers = {"X-SourceID" : vmc.id, "X-SharedKey" : vmc.key}
        r = requests.post(url=vmc.url, data=result, headers=headers)
        return True

    def senderRjid(self, mess):
        show, status, rjid = self.seen.get(mess.getFrom())
        return rjid.split('@')[0]

if __name__ == '__main__':

    # Grabbing values from imported config file
    morgooglie = VMBot(vmc.username, vmc.password, vmc.res, only_direct=False)
    morgooglie.join_room(vmc.chatroom1, vmc.nickname)
    morgooglie.join_room(vmc.chatroom2, vmc.nickname)
    morgooglie.serve_forever()
