# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import cgi


def format_ref_type(ref_type):
    return ref_type.replace('_', ' ').title()


def format_affil(char_name, sec_status, birthday, corp_name,
                 ally_name, fac_name, corp_ticker, alliance_ticker):
    """Represent character or structure data in a common format."""
    reply = ("<strong>{}</strong> ({:+.2f}, born {:%m/%Y}) ".format(char_name, sec_status, birthday)
             + "is part of ") if char_name else "The structure is owned by "

    reply += "<strong>{} {}</strong>".format(
        corp_name, format_tickers(corp_ticker, None, html=True)
    )

    if ally_name:
        reply += " in <strong>{} {}</strong>".format(
            ally_name, format_tickers(None, alliance_ticker, html=True)
        )

    if fac_name:
        reply += ", which belongs to the <strong>{}</strong>".format(fac_name)

    return reply


def format_tickers(corp_ticker, alliance_ticker, html=False):
    """Format ticker(s) like the default EVE client does."""
    tickers = []

    if corp_ticker:
        tickers.append("[{}]".format(corp_ticker))
    if alliance_ticker:
        tickers.append("<{}>".format(alliance_ticker))

    esc = cgi.escape if html else lambda x: x
    return esc(' '.join(tickers))


def format_jid_nick(jid, nick):
    """Join a JID with a nickname for output, if present."""
    jid = jid.split('@', 1)[0]
    if nick is not None:
        return "{} ({})".format(nick, jid)

    return jid


def disambiguate(given, like, category):
    """Disambiguate a list of names from the same category."""
    reply = 'Other {} like "{}": {}'.format(category, given, ", ".join(like[:3]))
    if len(like) > 3:
        reply += ", and {:,} others".format(len(like) - 3)

    return reply
