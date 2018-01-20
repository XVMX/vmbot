# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from os import path, pardir

_DATADIR = path.abspath(path.join(path.dirname(__file__), pardir, "data"))

EMOTES = path.join(_DATADIR, "emotes.txt")
HANDEY_QUOTES = path.join(_DATADIR, "handeysay.txt")
STATICDATA_DB = path.join(_DATADIR, "staticdata.sqlite")
BOT_DB = path.join(_DATADIR, "vmbot.db")
