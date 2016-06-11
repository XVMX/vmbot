# coding: utf-8

from os import path, pardir

_DATADIR = path.abspath(path.join(path.dirname(__file__), pardir, "data"))

CONFIG = path.join(_DATADIR, "vmbot.cfg")
EMOTES = path.join(_DATADIR, "emotes.txt")
STATICDATA_DB = path.join(_DATADIR, "staticdata.sqlite")
WH_DB = path.join(_DATADIR, "wh.db")
CACHE_DB = path.join(_DATADIR, "cache.db")
