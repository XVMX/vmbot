# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
import cgi

from bs4 import BeautifulSoup

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.helpers import api
from vmbot.models.message import Message

import config

MAIL_INTERVAL = 60 * 60
MAIL_FMT = "<strong>{}</strong> by <em>{}</em>"


def init(session, token):
    if "esi-mail.read_mail.v1" not in token.scopes:
        print('SSO token is missing "esi-mail.read_mail.v1" scope')
        return

    try:
        mails = token.request_esi("/v1/characters/{}/mail/", (token.character_id,))
    except APIError as e:
        print(unicode(e))
        return

    last_mail = (mails[0]['mail_id'], mails[0]['timestamp']) if mails else (None, None)

    Storage.set(session, "evemail_last_mail", last_mail)
    Storage.set(session, "evemail_next_run", time.time())


def needs_run(session):
    return Storage.get(session, "evemail_next_run") <= time.time()


def main(session, token):
    Storage.set(session, "evemail_next_run", time.time() + MAIL_INTERVAL)

    mails = read_mails(token, Storage.get(session, "evemail_last_mail"))
    if not mails:
        return

    Storage.set(session, "evemail_last_mail", (mails[0]['mail_id'], mails[0]['timestamp']))

    corp_mails, ally_mails = [], []
    for mail in mails:
        recv_ids = {recv['recipient_id'] for recv in mail['recipients']}
        if config.ALLIANCE_ID in recv_ids:
            ally_mails.append(mail)
        elif config.CORPORATION_ID in recv_ids:
            corp_mails.append(mail)

    if not corp_mails and not ally_mails:
        return

    chars = api.get_names(*{mail['from'] for mail in corp_mails + ally_mails})
    corp_mails = [{'id': mail['mail_id'],
                   'header': MAIL_FMT.format(cgi.escape(mail['subject']), chars[mail['from']])}
                  for mail in corp_mails]
    ally_mails = [{'id': mail['mail_id'],
                   'header': MAIL_FMT.format(cgi.escape(mail['subject']), chars[mail['from']])}
                  for mail in ally_mails]

    if len(corp_mails) + len(ally_mails) > 3:
        if corp_mails:
            corp_res = "{} new corp mail(s):<br />".format(len(corp_mails))
            corp_res += "<br />".join(mail['header'] for mail in corp_mails)

            for room in config.JABBER['primary_chatrooms']:
                session.add(Message(room, corp_res, "groupchat"))

        if ally_mails:
            ally_res = "{} new alliance mail(s):<br />".format(len(ally_mails))
            ally_res += "<br />".join(mail['header'] for mail in ally_mails)

            for room in config.JABBER['primary_chatrooms']:
                session.add(Message(room, ally_res, "groupchat"))
    else:
        for mail in corp_mails + ally_mails:
            res = mail['header'] + "<br />" + get_mail_body(token, mail['id'])
            for room in config.JABBER['primary_chatrooms']:
                session.add(Message(room, res, "groupchat"))

    session.commit()


def read_mails(token, last_mail):
    all_mails = []

    mails = filter_mails(last_mail, get_mails(token))
    all_mails.extend(mails)

    # ESI returns up to 50 mails at once
    while len(mails) == 50:
        mails = filter_mails(last_mail, get_mails(token, last_id=mails[-1]['mail_id']))
        all_mails.extend(mails)

    return all_mails


def get_mails(token, last_id=None):
    if "esi-mail.read_mail.v1" not in token.scopes:
        return []

    params = {'last_mail_id': last_id}
    try:
        return token.request_esi("/v1/characters/{}/mail/", (token.character_id,), params=params)
    except APIError:
        return []


def filter_mails(last_mail, mails):
    last_id, last_update = last_mail

    idx = next((idx for idx, mail in enumerate(mails) if mail['mail_id'] == last_id), None)
    if idx is None and last_update is not None:
        # Fallback in case last_mail was deleted
        last_update = time.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")
        idx = next((idx for idx, mail in enumerate(mails)
                    if time.strptime(mail['timestamp'], "%Y-%m-%dT%H:%M:%SZ") <= last_update), None)

    return mails[:idx]


def get_mail_body(token, mail_id):
    if "esi-mail.read_mail.v1" not in token.scopes:
        return "<em>Failed to load mail body</em>"

    try:
        res = token.request_esi("/v1/characters/{}/mail/{}/", (token.character_id, mail_id))['body']
    except APIError:
        return "<em>Failed to load mail body</em>"

    # Use BeautifulSoup to translate EVE HTML markup into XHTML-IM (XEP-0071)
    html = BeautifulSoup(res, "html.parser")
    for t in html.find_all("font"):
        t.name = "span"
        style = ""

        if "color" in t.attrs and t['color'] != "#bfffffff":  # Default color is white (not black)
            style += "color: #" + t['color'][3:] + ";"  # Ignore alpha channel
        if "size" in t.attrs:
            style += "font-size: " + t['size'] + "pt;"

        t.attrs.clear()
        if style:
            t['style'] = style

    return unicode(html)
