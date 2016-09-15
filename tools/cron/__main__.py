# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from . import path
from . import km_feed
from . import news_feed

from vmbot.helpers import database as db

FEEDS = (km_feed, news_feed)

if __name__ == "__main__":
    session = db.Session()

    for feed in FEEDS:
        if feed.needs_run(session):
            feed.main(session)

    session.close()
