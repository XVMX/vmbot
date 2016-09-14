# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import cron.path
from cron import km_feed
from cron import news_feed

from vmbot.helpers import database as db

# Initialize database tables
db.init_db()

# Initialize feeds
session = db.Session()

km_feed.init(session)
news_feed.init(session)

session.close()
