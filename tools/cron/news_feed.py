# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
import cgi
import xml.etree.ElementTree as ET

from . import path
from .models import Storage

from vmbot.helpers.exceptions import APIError
from vmbot.helpers import api
from vmbot.models.messages import Message

import config

NEWS_FEED = "https://newsfeed.eveonline.com/en-US/44/articles/page/1/20"
DEVBLOG_FEED = "https://newsfeed.eveonline.com/en-US/2/articles/page/1/20"
FEED_NS = {'atom': "http://www.w3.org/2005/Atom", 'title': "http://ccp/custom",
           'media': "http://search.yahoo.com/mrss/"}
FEED_FMT = "<strong>{title}</strong> by <em>{author}</em>: {url}"


def init(session):
    try:
        news = ET.fromstring(api.request_api(NEWS_FEED).content)
        devblog = ET.fromstring(api.request_api(DEVBLOG_FEED).content)
    except APIError as e:
        print(unicode(e))
        return

    news_id = news.find("atom:entry[1]/atom:id", FEED_NS).text
    news_updated = news.find("atom:entry[1]/atom:updated", FEED_NS).text
    devblog_id = devblog.find("atom:entry[1]/atom:id", FEED_NS).text
    devblog_updated = devblog.find("atom:entry[1]/atom:updated", FEED_NS).text

    Storage.set(session, "news_feed_last_news", (news_id, news_updated))
    Storage.set(session, "news_feed_last_devblog", (devblog_id, devblog_updated))
    Storage.set(session, "news_feed_next_run", time.time())


def needs_run(session):
    return Storage.get(session, "news_feed_next_run") <= time.time()


def main(session):
    Storage.set(session, "news_feed_next_run", time.time() + 10 * 60)

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
        reply = ["{} new EVE news:".format(len(news))]
        reply += [FEED_FMT.format(**entry) for entry in news]

        for room in config.JABBER['primary_chatrooms']:
            session.add(Message(room, "<br />".join(reply), "groupchat"))
        session.commit()

        Storage.set(session, "news_feed_last_news", (news[0]['id'], news[0]['updated']))

    if devblogs:
        reply = ["{} new EVE devblog(s):".format(len(devblogs))]
        reply += [FEED_FMT.format(**entry) for entry in devblogs]

        for room in config.JABBER['primary_chatrooms']:
            session.add(Message(room, "<br />".join(reply), "groupchat"))
        session.commit()

        Storage.set(session, "news_feed_last_devblog",
                    (devblogs[0]['id'], devblogs[0]['updated']))


def read_feed(url, last_entry):
    last_id, last_update = last_entry

    feed = ET.fromstring(api.request_api(url).content)
    entries = [{'id': entry.find("atom:id", FEED_NS).text,
                'title': cgi.escape(entry.find("atom:title", FEED_NS).text),
                'author': entry.find("atom:author/atom:name", FEED_NS).text,
                'url': entry.find("atom:link[@rel='alternate']", FEED_NS).attrib['href'],
                'updated': entry.find("atom:updated", FEED_NS).text}
               for entry in feed.findall("atom:entry", FEED_NS)]

    # ISO 8601 (eg 2016-02-10T16:35:32Z)
    entries.sort(key=lambda x: time.strptime(x['updated'], "%Y-%m-%dT%H:%M:%SZ"), reverse=True)

    idx = next((idx for idx, entry in enumerate(entries) if entry['id'] == last_id), None)
    if idx is None:
        # Fallback in case CCP deletes the last entry
        last_update = time.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")
        idx = next((idx for idx, entry in enumerate(entries)
                    if time.strptime(entry['updated'], "%Y-%m-%dT%H:%M:%SZ") >= last_update), None)

    return entries[:idx]
