#!/usr/bin/env python
# coding: utf-8

# Copyright (C) 2010 Arthur Furlan <afurlan@afurlan.org>
# Copyright (C) 2012 Sascha Jüngling <sjuengling@gmail.com>
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# 
# On Debian systems, you can find the full text of the license in
# /usr/share/common-licenses/GPL-3


from jabberbot import JabberBot, botcmd
from datetime import datetime
import elementtree.ElementTree as ET
import time
import re
import logging
import random
import requests

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
        self.only_direct = kwargs.get('only_direct', False)
        try:
            del kwargs['only_direct']
        except KeyError:
            pass

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


class VMBot(MUCJabberBot):

	def __init__(self, *args, **kwargs):
		# initialize jabberbot
		super(VMBot, self).__init__(*args, **kwargs)
		
		# Lists and config options for use in the various methods
		self.eball_answers = ['Probably.', 'Rather likely.', 'Definitely.', 'Of course.', 'Probably not.', 'This is very questionable.', 'Unlikely.', 'Absolutely not.']
		self.fishisms = ["~The Python Way!~", "HOOOOOOOOOOOOOOOOOOOOOOO! SWISH!", "DIVERGENT ZONES!"]
		self.directors = ["jack_haydn", "thirteen_fish", "pimpin_yourhos", "petter_sandstad", "johann_tollefson", "petyr_baelich", "arele"]
		self.url = ""
		self.id = ""
		self.key = ""
		self.target = '[gs]_valar_morghulis@bcast.goonfleet.com' # [gs]_valar_morghulis@bcast.goonfleet.com     jack_haydn@goonfleet.com
		
	@botcmd
	def eightball(self, mess, args):
		'''eightball <question> - Provides insight into the future'''
		if len(args) == 0:
			reply = 'You will need to provide a question for me to answer.'
		else:
			reply = self.eball_answers[random.randint(0, len(self.eball_answers)-1)]
		self.send_simple_reply(mess, reply)

	@botcmd
	def evetime(self, mess, args):
		'''evetime [+offset] - Displays the current evetime and the resulting evetime of the offset, if provided'''
		evetime = time.gmtime()
		reply = 'The current EVE time is ' + time.strftime('%Y-%m-%d %H:%M:%S', evetime)
		if len(args) > 1 and args[1:].isdigit() and args[0] == '+':
			time_add = time.gmtime(time.time() + int(args[1:])*60*60)
			reply += ' and ' + args + ' hour(s) is ' + time.strftime('%Y-%m-%d %H:%M:%S', time_add)
		self.send_simple_reply(mess, reply)

	@botcmd
	def sayhi(self, mess, args):
		'''sayhi - Says hi to you!'''
		reply = "Hi " + self.get_sender_username(mess) + "!"
		self.send_simple_reply(mess, reply)
	
	@botcmd
	def fishsay(self, mess, args):
		'''fishsay - fishy wisdom.'''
		reply = self.fishisms[random.randint(0,len(self.fishisms)-1)]
		self.send_simple_reply(mess, reply)
	
	@botcmd
	def rtd(self, mess, args):
		'''rtd [dice count] [sides] - Roll the dice. If no dice count/sides are provided, one dice and six sides will be assumed.'''
		args = args.strip().split(' ')
		reply = ''
		result = ''
		if len(args) == 1 and not args[0].isdigit():
			dice = 1
			sides = 6
		elif len(args) == 1 and args[0].isdigit():
			dice = int(args[0])
			sides = 6
		elif len(args) == 2 and args[0].isdigit() and args[1].isdigit():
			dice = int(args[0])
			sides = int(args[1])
		else:
			reply = 'You need to provide none, one or two integer parameters.'

		if dice > 1000 or sides > 1000:
			reply = "I want to see those dice/seeing you throw that many dice, dude. I don't get paid, so find someone else to do that for you, tyvm."
		
		if len(reply) == 0:
			for i in range(dice):
				result += str([random.randint(1, sides)])
			reply = ' '.join(['I rolled', str(dice), 'dice with', str(sides), 'sides each. The result is:'] + [result])
				
		self.send_simple_reply(mess, reply)
		
	@botcmd
	def flipcoin(self, mess, args):
		'''flipcoin - flips a coin'''
		reply = random.choice(["Heads!", "Tails!"])
		self.send_simple_reply(mess, reply)
	
	@botcmd
	def bcast(self, mess, args):
		'''bcast vm <message> - Sends a message to XVMX members. Must be <=1kb including the tag line. "vm" required to avoid accidental bcasts, only works in dir chat. Do not abuse this or Solo's wrath shall be upon you.
		A hacked together piece of shit.
		API docs: https://goonfleet.com/index.php?/topic/178259-announcing-the-gsf-web-broadcast-system-and-broadcast-rest-like-api/
		'''
		
		srjid = self.senderRjid(mess)

		if args[:2] == 'vm' and len(args) > 3:
			if str(mess.getFrom()).split("@")[0] == 'vm_dir':
				if srjid in self.directors:
					broadcast = args[3:] + '\n\n *** This was a broadcast by ' + srjid + ' to ' + self.target + ' through VMBot at ' + time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()) + ' EVE. ***'
					if len(broadcast) <= 1024:
						if(self.sendBcast(broadcast)):
							reply = self.get_sender_username(mess) + ", I have sent your broadcast to " + self.target
						else:
							reply = "Something went wrong while sending the broadcast."
					else:
						reply = "This broadcast is too long; max length is 1024 characters including the automatically generated info line at the end. Please try again with less of a tale."
				else:
					reply = "You don't have the rights to send broadcasts."
			else:
				reply = "Broadcasting is only enabled in director chat."
				
		self.send_simple_reply(mess, reply)
	
	@botcmd
	def pickone(self, mess, args):
		'''pickone <option1> or <option2> [or <option3> ...] - Chooses an option for you'''
		args = args.strip().split(' or ')
		if len(args) > 1:
			reply = args[random.randint(0,len(args)-1)]
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
			if self.senderRjid(mess) == 'jack_haydn' and self.get_sender_username(mess) != nickname:
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
		target.text = self.target
		text = ET.SubElement(message, "text")
		text.text = broadcast
		result = '<?xml version="1.0"?>' + ET.tostring(messaging)
		#print result
		
		headers = {"X-SourceID" : self.id, "X-SharedKey" : self.key}
		r = requests.post(url=self.url, data=result, headers=headers)
		#print r.text
		return True
	
	def senderRjid(self, mess):
		show, status, rjid = self.seen.get(mess.getFrom())
		return rjid.split('@')[0]
		
if __name__ == '__main__':

    username = ''
    password = ''
    res      = 'vmbot'
    nickname = 'Morgooglie'
	chatroom1 = 'vm_dir@conference.goonfleet.com'
	chatroom2 = 'xvmx@conference.goonfleet.com'

	morgooglie = VMBot(username, password, res, only_direct=False)
	morgooglie.join_room(chatroom1, nickname)
	morgooglie.join_room(chatroom2, nickname)
	morgooglie.serve_forever()
