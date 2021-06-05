# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta
import logging

# Log level
LOGLEVEL = logging.INFO

# DB URL (see https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls)
# Leave at default to use built-in sqlite database
DB_URL = "sqlite"

# Jabber credentials
# Primary chatrooms: main corp channel(s), feeds will be posted there
# Director chatrooms: director channel(s), important data will be posted there
JABBER = {
    'username': "username@domain.tld",
    'password': "yourpassword",
    'res': "VMBot",
    'nickname': "BotNickname",
    'chatrooms': (
        "room1@conference.domain.tld",
        "room2@conference.domain.tld",
        "room3@conference.domain.tld"
    ),
    'primary_chatrooms': (
        "room1@conference.domain.tld",
    ),
    'director_chatrooms': (
        "room3@conference.domain.tld",
    )
}

# Bot owner's corporation/alliance id
CORPORATION_ID = 1234567890
ALLIANCE_ID = None

# TOTP account keys
TOTP_KEYS = {
    'account name': "account key"
}

# Custom revenue table columns
REVENUE_COLS = (
    ("< 3 months", timedelta(days=90)),
    ("Since 2018", datetime(2018, 1, 1))
)

# ESI
# Data sources: tranquility
# Languages: en, en-us, de, fr, ja, ru, ko
ESI = {
    'base_url': "https://esi.evetech.net",
    'datasource': "tranquility",
    'lang': "en-us"
}

# EVE SSO
# Base URLs: https://login.eveonline.com/v2 (TQ)
# Required scopes: esi-mail.read_mail.v1, esi-wallet.read_corporation_wallets.v1,
#                  esi-search.search_structures.v1, esi-universe.read_structures.v1,
#                  esi-markets.structure_markets.v1
SSO = {
    'base_url': "https://login.eveonline.com/v2",
    'client_id': "",
    'client_secret': "",
    'refresh_token': ""
}

# GSF Broadcast API
BCAST = {
    'url': "",
    'id': "",
    'key': "",
    'target': ""
}

# RC Blacklist API
BLACKLIST = {
    'url': "",
    'key': ""
}

# Google API key
# Required API: YouTube Data API v3
YT_KEY = ""

# GitHub personal access token
# Required scope: public_repo
# Used to automatically report outdated/deprecated ESI routes
GITHUB = {
    'user': "",
    'token': ""
}
