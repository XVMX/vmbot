# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import re

# Pubbie talk regex parts
PUBBIETALK = (
    "sup",
    "dank",
    "o7",
    "o\/",
    "m8",
    "retart",
    "rekt",
    "toon(?:ies)?",
    "iskies",
    "thann(?:y|ies)",
    "yolo",
    "swag",
    "wewlad",
    "rofl",
    "2?stronk",
    "lmao"
)

PUBBIE_REGEX = re.compile("(?:^|\s)(?:{})(?:$|\s)".format('|'.join(PUBBIETALK)), re.IGNORECASE)

ZKB_REGEX = re.compile("https?://zkillboard\.com/kill/(-?\d+)/?", re.IGNORECASE)
