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
JABBER = {
    'username': "username@domain.tld",
    'password': "yourpassword",
    'res': "VMBot",
    'nickname': "BotNickname",
    'chatrooms': (
        "room1@conference.domain.tld",
        "room2@conference.domain.tld",
        "room3@conference.domain.tld"
    )
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
