#!/usr/bin/env python
# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import cron.path
from cron import news_feed
from cron import wallet_update

from vmbot.helpers import database as db
from vmbot.helpers.sso import SSOToken

import config

# Initialize database tables
db.init_db()

session = db.Session()

# Initialize feeds
news_feed.init(session)

# Initialize API updates
token = SSOToken.from_refresh_token(config.SSO['refresh_token'])
wallet_update.init(session, token)

session.close()
