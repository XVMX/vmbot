# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import cron.path

from vmbot.helpers import database as db

# Initialize database tables
db.init_db()
