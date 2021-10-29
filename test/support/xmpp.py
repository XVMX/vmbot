# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from xmpp import JID, Message

BOT_JID = JID("bot@domain.tld/VMBot")
USER_JID = JID("user@domain.tld/home")
USER_MUC_JID = JID("muc@conference.domain.tld/UserNick")
ADMIN_JID = JID("admin@domain.tld/gjk28s")
ADMIN_MUC_JID = JID("muc@conference.domain.tld/AdminNick")


def mock_pm_mess(body, frm=USER_JID):
    return Message(to=BOT_JID, body=body, typ=b"chat", frm=frm)


def mock_muc_mess(body, frm=USER_MUC_JID):
    return Message(to=BOT_JID, body=body, typ=b"groupchat", frm=frm)


def mock_get_uname_from_mess(jid):
    def get_uname_from_mess(mess, full_jid=False):
        return jid if full_jid else jid.getNode()

    return get_uname_from_mess
