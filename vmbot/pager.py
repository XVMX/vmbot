# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta

from xmpp.protocol import JID

from .botcmd import botcmd
from .helpers.regex import TIME_OFFSET_REGEX
from .models import Note

NOTE_FMT = "Message from {} for {} sent at {:%Y-%m-%d %H:%M:%S}:\n{}"
REMINDER_FMT = "Reminder for {} set at {:%Y-%m-%d %H:%M:%S}:\n{}"


class Pager(object):
    @staticmethod
    def _process_args(args):
        args = [item.strip() for item in args.split(None, 1)]
        if len(args) < 2:
            raise ValueError("Please provide a username, a message to send, "
                             "and optionally a time offset: <user> [offset] <msg>")

        user, data = args
        delta, text = timedelta(), None
        try:
            days, hours, mins = TIME_OFFSET_REGEX.match(data).groups()
            delta = timedelta(days=int(days or 0), hours=int(hours or 0), minutes=int(mins or 0))
            text = data.split(None, 1)[1].strip()
        except AttributeError:
            text = data
        except IndexError:
            raise ValueError("Please provide a username, a message to send, "
                             "and optionally a time offset: <user> [offset] <msg>")

        return user, text, datetime.utcnow() + delta

    @botcmd
    def remindme(self, mess, args):
        """<offset> <msg> - Reminds you about <msg> in the current channel

        Reminders will be discarded 30 days after their offset ran out.
        <offset> format: 12d15h37m equals 12 days, 15 hours, and 37 minutes.
        Only days, hours, and minutes are supported.
        """
        if len(args.split(None, 1)) < 2:
            return "Please specify a time offset and a message"

        # _process_args parameter can always be split into 3 parts here
        user, text, offset = self._process_args(self.get_sender_username(mess) + ' ' + args)
        text = REMINDER_FMT.format(user, datetime.utcnow(), text)
        note = Note(user, text, offset, room=mess.getFrom().getStripped())

        Note.add_note(note)
        return "Reminder for {} will be sent at {:%Y-%m-%d %H:%M:%S}".format(user, offset)

    @botcmd
    def sendmsg(self, mess, args):
        """<user> [offset] <msg> - Sends <msg> to <user> in the current channel

        If [offset] is present, message delivery will be delayed until that
        amount of time has passed. Messages will be discarded 30 days after their offset ran out.
        [offset] format: 12d15h37m equals 12 days, 15 hours, and 37 minutes.
        Only days, hours, and minutes are supported.
        """
        try:
            user, text, offset = self._process_args(args)
            text = NOTE_FMT.format(self.get_uname_from_mess(mess), user, datetime.utcnow(), text)
            note = Note(user, text, offset, room=mess.getFrom().getStripped())
        except ValueError as e:
            return unicode(e)

        Note.add_note(note)
        return "Message for {} will be sent at {:%Y-%m-%d %H:%M:%S}".format(user, offset)

    @botcmd
    def sendpm(self, mess, args):
        """<user> [offset] <msg> - Sends <msg> to <user> via PM

        If [offset] is present, message delivery will be delayed until that
        amount of time has passed. Messages will be discarded 30 days after their offset ran out.
        [offset] format: 12d15h37m equals 12 days, 15 hours, and 37 minutes.
        Only days, hours, and minutes are supported.
        """
        try:
            user, text, offset = self._process_args(args)
            jid = (JID(node=user, domain=self.jid.getDomain()).getStripped()
                   if '@' not in user else user)
            text = NOTE_FMT.format(self.get_uname_from_mess(mess), user, datetime.utcnow(), text)
            note = Note(jid, text, offset, type_="chat")
        except ValueError as e:
            return unicode(e)

        Note.add_note(note)
        return "PM for {} will be sent at {:%Y-%m-%d %H:%M:%S}".format(user, offset)