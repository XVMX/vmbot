# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta
import logging

# Log level
LOGLEVEL = logging.INFO

# DB URL (see https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls)
# Leave at default to use built-in sqlite database
DB_URL = "sqlite"

# Feature flags (some additional features are enabled by setting certain credentials)
NEWS_FEED = True
EVEMAIL_FEED = True
ZKILL_FEED = True
PUBBIE_SMACKTALK = False
ZBOT = True
REVENUE_TRACKING = False

# Jabber credentials
# Primary chatrooms: main corp channel(s), feeds will be posted there (if enabled)
# Director chatrooms: director channel(s), some commands are restricted to those channels
JABBER = {
    'username': "username@domain.tld",
    'password': "yourpassword",
    'res': "VMBot",
    'nickname': "BotNickname",
    'chatrooms': {
        "room1@conference.domain.tld",
        "room2@conference.domain.tld",
        "room3@conference.domain.tld"
    },
    'primary_chatrooms': {
        "room1@conference.domain.tld"
    },
    'director_chatrooms': {
        "room3@conference.domain.tld"
    },
    'pm_blacklist': {
        "broadcast_bot@domain.tld"
    }
}

# Bot owner's corporation/alliance id
CORPORATION_ID = 1234567890
ALLIANCE_ID = None

# TOTP account keys
TOTP_KEYS = {
    'account name': "account key"
}

# Custom revenue table columns (REVENUE_TRACKING)
REVENUE_COLS = (
    ("< 3 months", timedelta(days=90)),
    ("Since 2018", datetime(2018, 1, 1))
)

# ESI
# Languages: en, en-us, de, fr, ja, ru, ko
ESI = {
    'base_url': "https://esi.evetech.net",
    'datasource': "tranquility",
    'lang': "en-us"
}

# EVE SSO (register an application at https://developers.eveonline.com/)
# Required scopes:
#   esi-search.search_structures.v1, esi-universe.read_structures.v1,
#   esi-markets.structure_markets.v1, esi-mail.read_mail.v1 (EVEMAIL_FEED),
#   esi-wallet.read_corporation_wallets.v1 (REVENUE_TRACKING)
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
    'targets': {
        'abbrev': ""
    }
}

# RC Blacklist API
BLACKLIST_URL = ""

# Google API key (https://cloud.google.com/docs/authentication/api-keys)
# Required API: YouTube Data API v3
# Used to post context for YouTube links. Leave empty to disable.
YT_KEY = ""

# GitHub personal access token (https://github.com/settings/tokens)
# Required scope: public_repo
# Used to automatically report outdated/deprecated ESI routes
GITHUB = {
    'user': "",
    'token': ""
}
