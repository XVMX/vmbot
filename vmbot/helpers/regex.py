# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import re

ZKB_REGEX = re.compile("https?://zkillboard\.com/kill/(\d+)/?", re.IGNORECASE)
