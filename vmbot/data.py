from os import path


_DATAPATH = path.join(path.dirname(__file__), "data")

CONFIG = path.join(_DATAPATH, "vmbot.cfg")
STATICDATA_DB = path.join(_DATAPATH, "staticdata.sqlite")
EMOTES = path.join(_DATAPATH, "emotes.txt")
CACHE_DB = path.join(_DATAPATH, "cache.db")
WH_DB = path.join(_DATAPATH, "wh.db")
