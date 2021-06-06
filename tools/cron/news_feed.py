# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
import cgi
import xml.etree.ElementTree as ET

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.helpers.time import RFC822_DATETIME_FMT
from vmbot.helpers import api
from vmbot.models.message import Message

import config

FEED_INTERVAL = 10 * 60
NEWS_FEED = "https://www.eveonline.com/rss"
FEED_FMT = '<a href="{url}">{title}</a> by <em>{author}</em>'


def init(session):
    if not config.NEWS_FEEDS:
        return

    try:
        news = read_feed(NEWS_FEED, (None, "Thu, 01 Jan 1970 00:00:00 GMT"))
    except APIError as e:
        print(unicode(e))
        return

    Storage.set(session, "news_feed_last_news", (news[0]['id'], news[0]['updated']))
    Storage.set(session, "news_feed_next_run", time.time() + FEED_INTERVAL)


def needs_run(session):
    return config.NEWS_FEEDS and Storage.get(session, "news_feed_next_run") <= time.time()


def main(session):
    Storage.set(session, "news_feed_next_run", time.time() + FEED_INTERVAL)

    try:
        news = read_feed(NEWS_FEED, Storage.get(session, "news_feed_last_news"))
    except APIError:
        return

    reply = "{} new EVE news:<br />".format(len(news)) if len(news) > 1 else ""
    reply += "<br />".join(FEED_FMT.format(**entry) for entry in news)

    for room in config.JABBER['primary_chatrooms']:
        session.add(Message(room, reply, "groupchat"))
    session.commit()

    Storage.set(session, "news_feed_last_news", (news[0]['id'], news[0]['updated']))


def read_feed(url, last_entry):
    last_id, last_update = last_entry

    feed = ET.fromstring(api.request_api(url).content)[0]
    entries = [{'id': entry.findtext("guid"),
                'title': cgi.escape(entry.findtext("title")),
                'author': entry.findtext("author"),
                'tags': {t.text for t in entry.iterfind("category")},
                'url': entry.findtext("link"),
                'updated': entry.findtext("pubDate")}
               for entry in feed.iterfind("item")]

    entries.sort(key=lambda x: time.strptime(x['updated'], RFC822_DATETIME_FMT), reverse=True)

    idx = next((idx for idx, entry in enumerate(entries) if entry['id'] == last_id), None)
    if idx is None:
        # Fallback in case CCP deletes the last entry
        last_update = time.strptime(last_update, RFC822_DATETIME_FMT)
        idx = next((idx for idx, entry in enumerate(entries)
                    if time.strptime(entry['updated'], RFC822_DATETIME_FMT) <= last_update), None)

    return entries[:idx]
