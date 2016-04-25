#!/usr/bin/env python
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

from .config import config as vmc

from .vmbot import VMBot


if __name__ == "__main__":
    logger = logging.getLogger(".jabberbot")
    logger.setLevel(logging.getLevelName(vmc['loglevel']))
    logger.addHandler(logging.StreamHandler())

    # Grabbing values from imported config file
    jbc = vmc['jabber']
    morgooglie = VMBot(jbc['username'], jbc['password'], jbc['res'], kmFeed=True, newsFeed=True)
    for room in jbc['chatrooms']:
        morgooglie.muc_join_room(room, jbc['nickname'])
    morgooglie.serve_forever()
