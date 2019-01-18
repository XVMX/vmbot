# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
import cgi
import xml.etree.ElementTree as ET

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.helpers.time import RFC822_DATETIME_FMT, ISO8601_DATETIME_FMT
from vmbot.helpers import api
from vmbot.models.message import Message

import config

FEED_INTERVAL = 10 * 60
NEWS_FEED = "https://www.eveonline.com/rss/news"
DEVBLOG_FEED = "https://www.eveonline.com/rss/dev-blogs"
FEED_FMT = "<strong>{title}</strong> by <em>{author}</em>: {url}"

# Updates will be shown if they are tagged with an allowed tag,
# unless they are also tagged with a blocked tag
UPDATES_FEED = "https://updates.eveonline.com/rss/"
UPDATE_FMT = '<a href="{url}">{title}</a>'
UPDATES_ALLOWED_TAGS = {"Account", "Alpha", "API", "Balance", "Characters", "Corporations",
                        "Exploration", "Industry", "Lowsec", "Market", "Nullsec", "Omega",
                        "Performance", "PVP", "Solo", "Sovereignty", "Spaceships", "Structures",
                        "The Agency", "thirdpartydevs", "UI/UX"}
UPDATES_BLOCKED_TAGS = {"SKINs"}


def init(session):
    try:
        news = read_feed(NEWS_FEED, RFC822_DATETIME_FMT, (None, "Thu, 01 Jan 1970 00:00:00 GMT"))
        devblogs = read_feed(DEVBLOG_FEED, RFC822_DATETIME_FMT,
                             (None, "Thu, 01 Jan 1970 00:00:00 GMT"))
        updates = read_feed(UPDATES_FEED, ISO8601_DATETIME_FMT, (None, "1970-01-01T00:00:00Z"))
    except APIError as e:
        print(unicode(e))
        return

    Storage.set(session, "news_feed_last_news", (news[0]['id'], news[0]['updated']))
    Storage.set(session, "news_feed_last_devblog", (devblogs[0]['id'], devblogs[0]['updated']))
    Storage.set(session, "news_feed_last_update", (updates[0]['id'], updates[0]['updated']))
    Storage.set(session, "news_feed_next_run", time.time())


def needs_run(session):
    return Storage.get(session, "news_feed_next_run") <= time.time()


def main(session):
    Storage.set(session, "news_feed_next_run", time.time() + FEED_INTERVAL)

    news, devblogs, updates = None, None, None
    try:
        news = read_feed(NEWS_FEED, RFC822_DATETIME_FMT,
                         Storage.get(session, "news_feed_last_news"))
    except APIError:
        pass
    try:
        devblogs = read_feed(DEVBLOG_FEED, RFC822_DATETIME_FMT,
                             Storage.get(session, "news_feed_last_devblog"))
    except APIError:
        pass
    try:
        updates = read_feed(UPDATES_FEED, ISO8601_DATETIME_FMT,
                            Storage.get(session, "news_feed_last_update"))
    except APIError:
        pass

    if news:
        reply = "{} new EVE news:<br />".format(len(news))
        reply += "<br />".join(FEED_FMT.format(**entry) for entry in news)

        for room in config.JABBER['primary_chatrooms']:
            session.add(Message(room, reply, "groupchat"))
        session.commit()

        Storage.set(session, "news_feed_last_news", (news[0]['id'], news[0]['updated']))

    if devblogs:
        reply = "{} new EVE devblog(s):<br />".format(len(devblogs))
        reply += "<br />".join(FEED_FMT.format(**entry) for entry in devblogs)

        for room in config.JABBER['primary_chatrooms']:
            session.add(Message(room, reply, "groupchat"))
        session.commit()

        Storage.set(session, "news_feed_last_devblog", (devblogs[0]['id'], devblogs[0]['updated']))

    if updates:
        Storage.set(session, "news_feed_last_update", (updates[0]['id'], updates[0]['updated']))
        updates = filter(lambda e: any(t in UPDATES_ALLOWED_TAGS for t in e['tags']), updates)
        updates = filter(lambda e: not any(t in UPDATES_BLOCKED_TAGS for t in e['tags']), updates)

        if updates:
            reply = "{} new EVE update(s): ".format(len(updates))
            reply += ", ".join(UPDATE_FMT.format(**entry) for entry in updates[:-1])
            if len(updates) >= 2:
                if len(updates) > 2:
                    reply += ','
                reply += " and "
            reply += UPDATE_FMT.format(**updates[-1])

            for room in config.JABBER['primary_chatrooms']:
                session.add(Message(room, reply, "groupchat"))
            session.commit()


def read_feed(url, datetime_fmt, last_entry):
    last_id, last_update = last_entry

    feed = ET.fromstring(api.request_api(url).content)[0]
    entries = [{'id': entry.findtext("guid"),
                'title': cgi.escape(entry.findtext("title")),
                'author': entry.findtext("author"),
                'tags': set(t.text for t in entry.iterfind("category")),
                'url': entry.findtext("link"),
                'updated': entry.findtext("pubDate")}
               for entry in feed.iterfind("item")]

    entries.sort(key=lambda x: time.strptime(x['updated'], datetime_fmt), reverse=True)

    idx = next((idx for idx, entry in enumerate(entries) if entry['id'] == last_id), None)
    if idx is None:
        # Fallback in case CCP deletes the last entry
        last_update = time.strptime(last_update, datetime_fmt)
        idx = next((idx for idx, entry in enumerate(entries)
                    if time.strptime(entry['updated'], datetime_fmt) <= last_update), None)

    return entries[:idx]
