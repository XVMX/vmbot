# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta

from xmpp.protocol import JID

from .botcmd import botcmd
from .helpers.decorators import inject_db
from .helpers.regex import TIME_OFFSET_REGEX
from .models import Note

NOTE_FMT = "Message from {} for {} sent at {:%Y-%m-%d %H:%M:%S}:\n{}"
REMINDER_FMT = "Reminder for {} set at {:%Y-%m-%d %H:%M:%S}:\n{}"


class Pager(object):
    @staticmethod
    def _process_pager_args(args):
        args = args.strip()

        quot_end = args.find('"', 1)
        if args.startswith('"') and quot_end != -1:
            # user is enclosed in quotes
            user = args[1:quot_end].strip()
            data = args[quot_end + 1:].strip()
        else:
            args = args.split(None, 1)
            if len(args) < 2:
                raise ValueError("Please provide a username, a message to send, "
                                 "and optionally a time offset: <user> [offset] <msg>")
            user, data = args

        delta, text = timedelta(), None
        try:
            days, hours, mins = TIME_OFFSET_REGEX.match(data).groups()
            delta = timedelta(days=int(days or 0), hours=int(hours or 0), minutes=int(mins or 0))
            text = data.split(None, 1)[1]
        except AttributeError:
            text = data
        except IndexError:
            raise ValueError("Please provide a username, a message to send, "
                             "and optionally a time offset: <user> [offset] <msg>")

        return user, text, datetime.utcnow() + delta

    @botcmd
    @inject_db
    def remindme(self, mess, args, session):
        """<offset> <msg> - Reminds you about msg in the current channel

        Reminders will be discarded 30 days after their offset ran out.
        offset format: 12d15h37m equals 12 days, 15 hours, and 37 minutes.
        Only days, hours, and minutes are supported.
        """
        if len(args.split(None, 1)) < 2:
            return "Please specify a time offset and a message"

        # _process_pager_args parameter can always be split into 3 parts here
        user, text, offset = self._process_pager_args(
            '"{}" {}'.format(self.get_sender_username(mess), args)
        )
        text = REMINDER_FMT.format(user, datetime.utcnow(), text)
        note = Note(user, text, offset, room=mess.getFrom().getStripped())

        Note.add_note(note, session)
        return "Reminder for {} will be sent at {:%Y-%m-%d %H:%M:%S}".format(user, offset)

    @botcmd
    @inject_db
    def sendmsg(self, mess, args, session):
        """<user> [offset] <msg> - Sends msg to user in the current channel

        If offset is present, message delivery will be delayed until that
        amount of time has passed. Messages will be discarded 30 days after their offset ran out.
        If user contains spaces, enclose user in quotes.
        offset format: 12d15h37m equals 12 days, 15 hours, and 37 minutes.
        Only days, hours, and minutes are supported.
        """
        try:
            user, text, offset = self._process_pager_args(args)
            text = NOTE_FMT.format(self.get_uname_from_mess(mess), user, datetime.utcnow(), text)
            note = Note(user, text, offset, room=mess.getFrom().getStripped())
        except ValueError as e:
            return unicode(e)

        Note.add_note(note, session)
        return "Message for {} will be sent at {:%Y-%m-%d %H:%M:%S}".format(user, offset)

    @botcmd
    @inject_db
    def sendpm(self, mess, args, session):
        """<user> [offset] <msg> - Sends msg to user via PM

        If offset is present, message delivery will be delayed until that
        amount of time has passed. Messages will be discarded 30 days after their offset ran out.
        If user contains spaces, enclose user in quotes.
        offset format: 12d15h37m equals 12 days, 15 hours, and 37 minutes.
        Only days, hours, and minutes are supported.
        """
        try:
            user, text, offset = self._process_pager_args(args)
            jid = (JID(node=user, domain=self.jid.getDomain()).getStripped()
                   if '@' not in user else user)
            text = NOTE_FMT.format(self.get_uname_from_mess(mess), user, datetime.utcnow(), text)
            note = Note(jid, text, offset, type_="chat")
        except ValueError as e:
            return unicode(e)

        Note.add_note(note, session)
        return "PM for {} will be sent at {:%Y-%m-%d %H:%M:%S}".format(user, offset)
