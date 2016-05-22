from os import path, pardir


_DATADIR = path.abspath(path.join(path.dirname(__file__), pardir, "data"))

CONFIG = path.join(_DATADIR, "vmbot.cfg")
STATICDATA_DB = path.join(_DATADIR, "staticdata.sqlite")
EMOTES = path.join(_DATADIR, "emotes.txt")
CACHE_DB = path.join(_DATADIR, "cache.db")
WH_DB = path.join(_DATADIR, "wh.db")
