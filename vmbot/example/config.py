# coding: utf-8

import logging

# Log level
LOGLEVEL = logging.INFO

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
