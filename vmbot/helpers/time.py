# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import timedelta
import re
from collections import Counter


# RFC 822 (eg Fri, 20 Apr 2018 14:00:00 GMT)
RFC822_DATETIME_FMT = "%a, %d %b %Y %H:%M:%S %Z"
# ISO 8601 (eg 2018-07-09T14:43:21Z)
ISO8601_DATETIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
# ISO 8601 with microseconds (eg 2018-07-09T14:43:21.602741Z)
ISO8601_DATETIME_MICRO_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

_ISO8601_DURATION_REGEX = re.compile(r"^P(?:([\d,.]+)Y)?(?:([\d,.]+)M)?"
                                     r"(?:([\d,.]+)W)?(?:([\d,.]+)D)?"
                                     r"(?:T(?:([\d,.]+)H)?(?:([\d,.]+)M)?(?:([\d,.]+)S)?)?$")
_ISO8601_DURATION_TBL = {
    0: ('days', 365),  # Years (~365 days)
    1: ('days', 30),  # Months (~30 days)
    2: ('weeks', 1),
    3: ('days', 1),
    4: ('hours', 1),
    5: ('minutes', 1),
    6: ('seconds', 1)
}


def _iso8601_dur_parse_group(idx, val):
    kw, kwval = _ISO8601_DURATION_TBL[idx]
    kwval *= val
    return timedelta(**{kw: kwval})


def parse_iso8601_duration(dur):
    """Parse an ISO 8601 formatted duration."""
    match = _ISO8601_DURATION_REGEX.match(dur)
    if match is None:
        return None

    res = timedelta(seconds=0)
    groups = match.groups()
    first_val = True
    for idx in reversed(xrange(len(groups))):
        g = groups[idx]
        if g is None:
            continue

        count = Counter(g)
        num_decs = count['.'] + count[',']
        if num_decs > 1 or (num_decs == 1 and not first_val):
            return None
        elif num_decs == 1:
            if count[','] == 1:
                g = g.replace(',', '.', 1)
            res += _iso8601_dur_parse_group(idx, float(g))
        else:
            res += _iso8601_dur_parse_group(idx, int(g))
        first_val = False

    return res
