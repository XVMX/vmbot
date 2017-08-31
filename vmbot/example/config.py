# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import logging

# Log level
LOGLEVEL = logging.INFO

# Jabber usernames allowed to execute director commands
DIRECTORS = (
    "username1",
    "username2",
    "username3"
)

# Jabber usernames allowed to execute admin commands
ADMINS = (
    "username1",
    "username2",
    "username3"
)

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

# Bot owner's corporationID
CORPORATION_ID = 1234567890

# ESI
# Data sources: tranquility, singularity
# Languages: en-us, de, fr, ja, ru, zh
ESI = {
    'base_url': "https://esi.tech.ccp.is",
    'datasource': "tranquility",
    'lang': "en-us"
}

# EVE SSO
# Base URLs: https://login.eveonline.com (TQ), https://sisilogin.testeveonline.com (Sisi)
# Required scopes: characterNotificationsRead, corporationWalletRead,
#                  corporationAssetsRead, corporationStructuresRead
SSO = {
    'base_url': "https://login.eveonline.com",
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
