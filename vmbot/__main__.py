# coding: utf-8

# Copyright (C) 2010 Arthur Furlan <afurlan@afurlan.org>
# Copyright (c) 2013 Sascha J�ngling <sjuengling@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# On Debian systems, you can find the full text of the license in
# /usr/share/common-licenses/GPL-3

import logging
from logging.handlers import TimedRotatingFileHandler

from .config import config
from . import VMBot

if __name__ == "__main__":
    logger = logging.getLogger("vmbot")
    logger.setLevel(logging.getLevelName(config['loglevel']))
    handler = TimedRotatingFileHandler("vmbot.log", when='d', interval=7,
                                       backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)

    jbc = config['jabber']
    morgooglie = VMBot(jbc['username'], jbc['password'], jbc['res'], km_feed=True, news_feed=True)
    for room in jbc['chatrooms']:
        morgooglie.muc_join_room(room, jbc['nickname'])

    try:
        morgooglie.serve_forever()
    except Exception:
        logger.exception("An error happened in the main loop:")
        morgooglie.shutdown()

    logging.shutdown()
