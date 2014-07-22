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
import subprocess
import json

from sympy.printing.pretty import pretty
from sympy.parsing.sympy_parser import parse_expr
import vmbot_config as vmc

logger = logging.getLogger('jabberbot')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
logger.addHandler(ch)

class MUCJabberBot(JabberBot):

    ''' Add features in JabberBot to allow it to handle specific
    characteristics of multiple users chatroom (MUC). '''

    PING_FREQUENCY = 60  # overriding JabberBot base class
    PING_TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        ''' Initialize variables. '''
        self.nick_dict = {}

        # answer only direct messages or not?
        self.only_direct = kwargs.pop('only_direct', False)

        # initialize jabberbot
        super(MUCJabberBot, self).__init__(*args, **kwargs)

        # create a regex to check if a message is a direct message
        user, domain = str(self.jid).split('@')
        self.direct_message_re = re.compile('^%s(@%s)?[^\w]? ' \
                % (user, domain))

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

        # change this to be limited to certain people if you want by
        # if self.get_sender_username(mess) == 'solodrakban":
        if mess.getType() != "groupchat":  # solodrakban protection
            return

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
    # 8ball answers like the original, as per http://en.wikipedia.org/wiki/Magic_8-Ball
    eball_answers = ['It is certain', 'It is decidedly so', 'Without a doubt', 'Yes definitely', 'You may rely on it', 'As I see it, yes', 'Most likely', 'Outlook good', 'Yes', 'Signs point to yes', 'Reply hazy try again', 'Ask again later', 'Better not tell you now', 'Cannot predict now', 'Concentrate and ask again', 'Don\'t count on it', 'My reply is no', 'My sources say no', 'Outlook not so good', 'Very doubtful']
    fishisms = ["~The Python Way!~", "HOOOOOOOOOOOOOOOOOOOOOOO! SWISH!", "DIVERGENT ZONES!", "BONUSSCHWEIN! BONUSSCHWEIN!"]
    pimpisms = ["eabod","why do you hate black people?", "i want a bucket full of money covered rainbows","bundle of sticks"]
    chaseisms = ["would you PLEASE"]
    nickisms = ["D00d!", "But d00d!", "Come on d00d...", "Oh d00d", "D0000000000000000000000000000000d!", "D00d, never go full retart!"]
    directors = ["jack_haydn", "thirteen_fish", "pimpin_yourhos", "johann_tollefson", "petyr_baelich", "arele", "kairk_efraim", "lofac", "jons_squire"]
    admins = ["jack_haydn", "thirteen_fish"]

    def __init__(self, *args, **kwargs):
        # initialize jabberbot
        super(VMBot, self).__init__(*args, **kwargs)

    @botcmd
    def math(self, mess, args):
        '''<expr> - Evaluates expr mathematically. If you want decimal results, force floating point numbers by doing 4.0/3 instead of 4/3'''

        @timeout(10, "Sorry, this query took too long to execute and I had to kill it off.")
        def do_math(args):
            return pretty(parse_expr(args), full_prec=False, use_unicode=True)

        try:
            reply = do_math(args)
            if '\n' in reply:
                reply = '\n' + reply

            reply = '<font face="monospace">' + re.sub('[\n]','</font><br/><font face="monospace">',reply) + '</font>'
        except Exception, e:
            reply = str(e)

        if len(reply) > 2 ** 15:  # TODO: what is the actual bound?
            reply = "I've evaluated your expression but it's too long to send with jabber"
        return reply

    @botcmd(name="8ball")
    def bot_8ball(self, mess, args):
        '''<question> - Provides insight into the future'''
        if len(args) == 0:
            return 'You will need to provide a question for me to answer.'
        else:
            return random.choice(self.eball_answers)

    @botcmd
    def evetime(self, mess, args):
        '''[+offset] - Displays the current evetime and the resulting evetime of the offset, if provided'''
        timefmt = '%Y-%m-%d %H:%M:%S'
        evetime = datetime.utcnow()
        reply = 'The current EVE time is ' + evetime.strftime(timefmt)
        try:
            offset_time = timedelta(hours=int(args)) + evetime
            reply += ' and {} hour(s) is {}'.format(args.strip(), offset_time.strftime(timefmt))
        except ValueError:
            pass
        return reply

    @botcmd
    def sayhi(self, mess, args):
        '''Says hi to you!'''
        return "Hi " + self.get_sender_username(mess) + "!"

    @botcmd(hidden=True)
    def every(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "lion"

    @botcmd(hidden=True)
    def lion(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "except"

    @botcmd(hidden=True, name="except")
    def bot_except(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "for"

    @botcmd(hidden=True, name="for")
    def bot_for(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "at"

    @botcmd(hidden=True)
    def at(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "most"

    @botcmd(hidden=True, name="most")
    def bot_most(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "one"

    @botcmd(hidden=True, name="one")
    def bot_one(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return ":bravo:"

    @botcmd(hidden=True, name="z")
    def bot_z(self, mess, args):
        '''z0r'''
        if not args and random.randint(1, 3) == 1:
            return "0"

    @botcmd(hidden=True, name="0")
    def bot_0(self, mess, args):
        '''z0r'''
        if not args and random.randint(1, 3) == 1:
            return "r"

    @botcmd(hidden=True, name="r")
    def bot_r(self, mess, args):
        '''z0r'''
        if not args and random.randint(1, 3) == 1:
            return "z"

    @botcmd
    def fishsay(self, mess, args):
        '''Fishy wisdom.'''
        return random.choice(self.fishisms)

    @botcmd
    def pimpsay(self, mess, args):
        '''Like fishsay but blacker'''
        return random.choice(self.pimpisms)

    @botcmd
    def nicksay(self, mess, args):
        '''Like fishsay but pubbietasticer'''
        return random.choice(self.nickisms)

    @botcmd
    def chasesay(self, mess, args):
        '''Please'''
        cmdname = self.chasesay._jabberbot_command_name
        if args[:len(cmdname)] == cmdname:
            return "nope"
        if len(args) > 0:
            name = args.strip()
        else:
            name = self.get_sender_username(mess)
        return name + ', ' + self.chaseisms[0]

    @botcmd
    def rtd(self, mess, args):
        '''Like a box of chocolates, you never know what you're gonna get'''
        emotes = open("emotes.txt", 'r')
        remotes = emotes.read().split('\n')
        emotes.close()

        while not remotes.pop(0).startswith('[default]'):
            pass

        return random.choice(remotes).split()[-1]

    @botcmd
    def dice(self, mess, args):
        '''[dice count] [sides] - Roll the dice. If no dice count/sides are provided, one dice and six sides will be assumed.'''
        dice = 1
        sides = 6
        try:
            args = args.strip().split()
            if len(args) > 2:
                raise VMBotError('You need to provide none, one or two parameters.')

            try:
                dice = int(args[0])
                sides = int(args[1])
            except ValueError:
                raise VMBotError('You need to provide integer parameters.')
            except IndexError:
                pass

            if dice not in xrange(50):
                raise VMBotError("That's an absurd number of dice, try again")
            if sides not in xrange(1, 2 ** 8):
                raise VMBotError("That's an absurd number of sides, try again")

            result = ''
            for i in range(dice):
                result += str([random.randint(1, sides)])
            reply = 'I rolled {} dice with {} sides each. The result is {}'.format(dice, sides, result)
        except VMBotError, e:
            reply = str(e)
        finally:
            return reply

    @botcmd
    def flipcoin(self, mess, args):
        '''flips a coin'''
        return random.choice(["Heads!", "Tails!"])

    @botcmd
    def bcast(self, mess, args):
        ''' vm <message> - Sends a message to XVMX members. Must be <=1kb including the tag line. "vm" required to avoid accidental bcasts, only works in dir chat. Do not abuse this or Solo's wrath shall be upon you.
        A hacked together piece of shit.
        API docs: https://goonfleet.com/index.php?/topic/178259-announcing-the-gsf-web-broadcast-system-and-broadcast-rest-like-api/
        '''
        if args[:2] != 'vm' or len(args) <= 3:
            return

        srjid = self.get_uname_from_mess(mess)

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

        return reply

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
            return self.get_sender_username(mess) + ': Pong.'
        else:
            return 'Pong.'

    @botcmd(hidden=True)
    def reload(self, mess, args):
        '''reload - Kills the bot's process. If ran in a while true loop on the shell, it'll immediately reconnect.'''
        if len(args) == 0:
            if self.get_uname_from_mess(mess) in self.admins and self.get_sender_username(mess) != vmc.nickname:
                reply = 'afk shower'
                self.quit()
            else:
                reply = 'You are not authorized to reload the bot, please go and DIAF!'

            return reply

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

        headers = {"X-SourceID" : vmc.id, "X-SharedKey" : vmc.key}
        r = requests.post(url=vmc.url, data=result, headers=headers)
        return True

    #@botcmd
    def google(self, mess, args):
        # Currently defunct since Google nuked the Calc api with the removal of iGoogle
        '''<query> - Forwards <query> to the google calculator API and returns the results. Try "50 fahrenheit in celsius" for example. Currently defunct since Google nuked the Calc api with the removal of iGoogle'''
        response = requests.get("http://www.google.com/ig/calculator", params={"hl" : "en", "q" : args})

        # Fix the Google Calc's faulty API responses
        fixed = u"{"
        for touple in response.text[1:-1].split(','):
            (k, v) = touple.split(':')
            fixed += '"%s" : %s,' % (k, v)
        fixed = fixed[:-1] + "}"
        fixed = json.loads(fixed)
        try:
            if fixed['error']:
                raise VMBotError("An error occurred. Sometimes Google accepts unit shorthands (40f in c), sometimes it doesn't (4 megabyte in megabit). Check if that's the issue. Alternatively, it simply might not be able to do what you are trying.")
            else:
                reply = ''.join([fixed['lhs'], ' = <b>', fixed['rhs'], '</b>'])
        except VMBotError, e:
            reply = str(e)

        return reply

    @botcmd(hidden=False)
    def rcbl(self, mess, args):
        '''<pilot name> - Asks the RC API if <pilot name> has an entry in the blacklist. Multiple pilots possible via comma separated list (no spaces around commas).'''
        try:
            reply = 'Sorry, something went wrong.'
            args = args.split(',')
            result = ''
            # Remove verify=False as soon as python 2.7.7 hits (exp. May 31, 2014). Needed due to self-signed cert with multiple domains + requests/urllib3
            # Ref.: https://github.com/kennethreitz/requests/issues/1977 http://legacy.python.org/dev/peps/pep-0466/ http://legacy.python.org/dev/peps/pep-0373/
            for pilot in args:
                response = requests.get(''.join([vmc.blurl, vmc.blkey, '/', pilot]), verify=False)
                print response.json()[0]['output']
                result += ''.join([pilot, ' is ', response.json()[0]['output'], ' <br />'])

            reply = result
        except VMBotError, e:
            reply = str(e)
        finally:
            return reply


    @botcmd(hidden=True)
    # Very rough hack, needs validation and shit
    def goosolve(self, mess, args):
        '''goosolve - Calculates R16 price points. Params: <r64 price> <r32 price> <alch profit/mo>, defaults are 60k, 25k, 400m.'''
        if len(args) == 0:
            r64 = '60000';
            r32 = '25000';
            maxAlch = '400000000';
        else:
            (r64, r32, maxAlch) = args.split(" ")[:3]

        recipes = []
        recipe = []
        recipe += ["Fluxed Condensates"]
        recipe += [parse_expr("("+r64+"*100*2)/200*1.15")]
        recipe += ["100 <b>plat</b> + 5 van"]
        recipe += [parse_expr("solve(Eq((40*"+str(recipe[1])+"-(14000*5+x*100.))*24*30, "+maxAlch+".), x)")]
        recipes += [recipe]
        recipe = []

        recipe += ["Neo Mercurite"]
        recipe += [parse_expr("("+r32+"*100+"+r64+"*100)/200*1.15")]
        recipe += ["100 <b>plat</b> + 5 merc"]
        recipe += [parse_expr("solve(Eq((40*"+str(recipe[1])+"-("+r32+"*5+x*100.))*24*30, "+maxAlch+".), x)")]
        recipes += [recipe]
        recipe = []

        recipe += ["Thulium Hafnite"]
        recipe += [parse_expr("("+r32+"*100+"+r64+"*100)/200*1.15")]
        recipe += ["100 <b>van</b> + 5 haf"]
        recipe += [parse_expr("solve(Eq((40*"+str(recipe[1])+"-("+r32+"*5+x*100.))*24*30, "+maxAlch+".), x)")]
        recipes += [recipe]
        recipe = []

        recipe += ["Dysporite"]
        recipe += [parse_expr("("+r32+"*100+"+r64+"*100)/200*1.15")]
        recipe += ["100 <b>cad</b> + 5 merc"]
        recipe += [parse_expr("solve(Eq((40*"+str(recipe[1])+"-("+r32+"*5+x*100.))*24*30, "+maxAlch+".), x)")]
        recipes += [recipe]
        recipe = []

        recipe += ["Ferrofluid"]
        recipe += [parse_expr("("+r32+"*100+"+r64+"*100)/200*1.15")]
        recipe += ["100 <b>cad</b> + 5 haf"]
        recipe += [parse_expr("solve(Eq((40*"+str(recipe[1])+"-("+r32+"*5+x*100.))*24*30, "+maxAlch+".), x)")]
        recipes += [recipe]
        recipe = []

        recipe += ["Hyperflurite"]
        recipe += [parse_expr("(14000*100+"+r64+"*100)/200*1.15")]
        recipe += ["100 <b>chrom</b> + 5 van"]
        recipe += [parse_expr("solve(Eq((40*"+str(recipe[1])+"-(14000*5+x*100.))*24*30, "+maxAlch+".), x)")]
        recipes += [recipe]
        recipe = []

        recipe += ["Prometium"]
        recipe += [parse_expr("(14000*100+"+r64+"*100)/200*1.15")]
        recipe += ["100 <b>chrom</b> + 5 cad"]
        recipe += [parse_expr("solve(Eq((40*"+str(recipe[1])+"-(14000*5+x*100.))*24*30, "+maxAlch+".), x)")]
        recipes += [recipe]
        recipe = []

        reply = "Calculating R16 price points, with R64s = {:,}, R32s = {:,}, max. monthly alchemy profit = {:,}.<br />".format(int(r64),int(r32),int(maxAlch))
        reply += "<span style=\"font-family:Courier\">{:32}{:23}{:30}{:20}".format("<b>Normal reaction</b>", "<b>Price Target</b>", "<b>Alchemy Reaction</b>", "<b>R16 price target</b><br />")

        for i in range(len(recipes)):
            reply += "{:25}{:<16,d}{:<30}{:<20,d}<br />".format(recipes[i][0], int(recipes[i][1]), recipes[i][2], int(str(recipes[i][3])[1:-12]))
        return reply+"</span>"

    @botcmd(hidden=True)
    def gitpull(self, mess, args):
        '''gitpull - pulls the latest commit from the bot repository and updates the bot with it.'''
        srjid = self.get_uname_from_mess(mess)
        try:
            if str(mess.getFrom()).split("@")[0] != 'vm_dir':
                raise VMBotError("git pull is only enabled in director chat.")

            if srjid not in self.admins:
                raise VMBotError("You don't have the rights to git pull.")

            p = subprocess.Popen(['git', 'pull', ], cwd=r'/home/sjuengling/vmbot/', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            reply = ('\n').join([out, err]).strip()
        except VMBotError, e:
            reply = str(e)

        return reply


if __name__ == '__main__':

    # Grabbing values from imported config file
    morgooglie = VMBot(vmc.username, vmc.password, vmc.res, only_direct=False, acceptownmsgs=True)
    morgooglie.join_room(vmc.chatroom1, vmc.nickname)
    morgooglie.join_room(vmc.chatroom2, vmc.nickname)
    morgooglie.join_room(vmc.chatroom3, vmc.nickname)
    morgooglie.serve_forever()
