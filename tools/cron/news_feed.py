# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
import cgi
import xml.etree.ElementTree as ET

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.helpers import api
from vmbot.models.message import Message

import config

FEED_INTERVAL = 10 * 60
NEWS_FEED = "https://www.eveonline.com/rss/news"
DEVBLOG_FEED = "https://www.eveonline.com/rss/dev-blogs"
FEED_FMT = "<strong>{title}</strong> by <em>{author}</em>: {url}"


def init(session):
    try:
        news = ET.fromstring(api.request_api(NEWS_FEED).content)[0]
        devblog = ET.fromstring(api.request_api(DEVBLOG_FEED).content)[0]
    except APIError as e:
        print(unicode(e))
        return

    news_id = news.find("item[1]/guid").text
    news_updated = news.find("item[1]/pubDate").text
    devblog_id = devblog.find("item[1]/guid").text
    devblog_updated = devblog.find("item[1]/pubDate").text

    Storage.set(session, "news_feed_last_news", (news_id, news_updated))
    Storage.set(session, "news_feed_last_devblog", (devblog_id, devblog_updated))
    Storage.set(session, "news_feed_next_run", time.time())


def needs_run(session):
    return Storage.get(session, "news_feed_next_run") <= time.time()


def main(session):
    Storage.set(session, "news_feed_next_run", time.time() + FEED_INTERVAL)

    news, devblogs = None, None
    try:
        news = read_feed(NEWS_FEED, Storage.get(session, "news_feed_last_news"))
    except APIError:
        pass
    try:
        devblogs = read_feed(DEVBLOG_FEED, Storage.get(session, "news_feed_last_devblog"))
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


def read_feed(url, last_entry):
    last_id, last_update = last_entry

    feed = ET.fromstring(api.request_api(url).content)[0]
    entries = [{'id': entry.find("guid").text,
                'title': cgi.escape(entry.find("title").text),
                'author': entry.find("author").text,
                'url': entry.find("link").text,
                'updated': entry.find("pubDate").text}
               for entry in feed.findall("item")]

    # RFC 822 (eg Fri, 20 Apr 2018 14:00:00 GMT)
    DATETIME_FMT = "%a, %d %b %Y %H:%M:%S %Z"
    entries.sort(key=lambda x: time.strptime(x['updated'], DATETIME_FMT), reverse=True)

    idx = next((idx for idx, entry in enumerate(entries) if entry['id'] == last_id), None)
    if idx is None:
        # Fallback in case CCP deletes the last entry
        last_update = time.strptime(last_update, DATETIME_FMT)
        idx = next((idx for idx, entry in enumerate(entries)
                    if time.strptime(entry['updated'], DATETIME_FMT) <= last_update), None)

    return entries[:idx]
