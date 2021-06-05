# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import re

# Pubbie talk regex parts
PUBBIETALK = (
    "sup",
    "dank",
    "o7",
    "o/",
    r"\o",
    "m8",
    "retart",
    "rekt",
    "toon(?:ies)?",
    "iskies",
    "(?:thann?|chimm?|nidd?|dess)(?:y|ies)",
    "yolo",
    "swag",
    "wewlad",
    "2?stronk",
    "linky"
)

PUBBIE_REGEX = re.compile(r"\b(?:{})\b".format('|'.join(PUBBIETALK)), re.IGNORECASE)

ZKB_REGEX = re.compile(r"(?:https?://)?zkillboard\.com/kill/(-?\d+)/?", re.IGNORECASE)

YT_REGEX = re.compile((r"(?:https?://)?(?:(?:(?:m|www)\.)?youtube\.com|youtu\.be)"
                       r"/(?:[\w-]+\?v=|embed/|v/)?([\w-]+)"), re.IGNORECASE)

TIME_OFFSET_REGEX = re.compile(r"^(?!\s|$)(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:\s|$)", re.IGNORECASE)
