# coding: utf-8

from os import path, pardir

_DATADIR = path.abspath(path.join(path.dirname(__file__), pardir, "data"))

EMOTES = path.join(_DATADIR, "emotes.txt")
STATICDATA_DB = path.join(_DATADIR, "staticdata.sqlite")
BOT_DB = path.join(_DATADIR, "vmbot.db")
