# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
import re
import cgi

from bs4 import BeautifulSoup, NavigableString

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.helpers.time import ISO8601_DATETIME_FMT
from vmbot.helpers import api
from vmbot.models.message import Message

import config

MAIL_INTERVAL = 60 * 60
MAIL_FMT = "<strong>{}</strong> by <em>{}</em>"
REPLY_REGEX = re.compile(r"-{32}")
KILLREPORT_REGEX = re.compile(r"killReport:(\d+):[0-9a-f]+", re.IGNORECASE)


def init(session, token):
    if not config.EVEMAIL_IDS:
        return

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
    Storage.set(session, "evemail_next_run", time.time() + MAIL_INTERVAL)


def needs_run(session):
    return config.EVEMAIL_IDS and Storage.get(session, "evemail_next_run") <= time.time()


def main(session, token):
    Storage.set(session, "evemail_next_run", time.time() + MAIL_INTERVAL)

    mails = read_mails(token, Storage.get(session, "evemail_last_mail"))
    if not mails:
        return

    Storage.set(session, "evemail_last_mail", (mails[0]['mail_id'], mails[0]['timestamp']))

    mails = [m for m in mails
             if any(r['recipient_id'] in config.EVEMAIL_IDS for r in m['recipients'])]
    if not mails:
        return

    chars = api.get_names(*{m['from'] for m in mails})
    mails = [{'id': m['mail_id'],
              'header': MAIL_FMT.format(cgi.escape(m['subject']), chars[m['from']])}
             for m in mails]

    if len(mails) > 3:
        res = "{} new EVE mail(s):<br />".format(len(mails))
        res += "<br />".join(m['header'] for m in mails)

        for room in config.JABBER['primary_chatrooms']:
            session.add(Message(room, res, "groupchat"))
    else:
        for m in mails:
            res = m['header']
            body = get_mail_body(token, m['id'])
            if body:
                res += "<br />" + body

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
        last_update = time.strptime(last_update, ISO8601_DATETIME_FMT)
        idx = next((idx for idx, mail in enumerate(mails)
                    if time.strptime(mail['timestamp'], ISO8601_DATETIME_FMT) <= last_update), None)

    return mails[:idx]


def get_mail_body(token, mail_id):
    if "esi-mail.read_mail.v1" not in token.scopes:
        return "<em>Failed to load mail body</em>"

    try:
        res = token.request_esi("/v1/characters/{}/mail/{}/", (token.character_id, mail_id))['body']
    except APIError:
        return "<em>Failed to load mail body</em>"

    # Remove reply chains from mail body
    html = BeautifulSoup(res, "html.parser")
    t = html.find(string=REPLY_REGEX)
    if t is not None:
        while t is not html:
            while t.next_sibling is not None:
                t.next_sibling.extract()
            tmp = t
            t = t.parent
            if isinstance(tmp, NavigableString) or not tmp.contents:
                tmp.extract()

    # Strip empty trailing tags (including linebreaks)
    for t in reversed(list(html.descendants)):
        if isinstance(t, NavigableString) and t.strip():
            break
        t.extract()

    # Translate EVE font markup into XHTML-IM (XEP-0071)
    for t in html.find_all("font"):
        t.name = "span"
        style = ""

        if "color" in t.attrs and t['color'] != "#ff999999":  # Default color is grey (not black)
            style += "color: #" + t['color'][3:] + ";"  # Ignore alpha channel
        if "size" in t.attrs:
            style += "font-size: " + t['size'] + "pt;"

        t.attrs.clear()
        if style:
            t['style'] = style

    for t in html.find_all("a"):
        try:
            href = t['href']
        except KeyError:
            continue

        # Remove EVE's custom showinfo: scheme links
        if href.startswith("showinfo:"):
            t.name = "span"
            t.attrs.clear()
            continue

        # Replace EVE's custom killReport: scheme links with zKB links
        m = KILLREPORT_REGEX.match(href)
        if m is not None:
            t['href'] = "https://zkillboard.com/kill/{}/".format(m.group(1))
            continue

    return unicode(html)
