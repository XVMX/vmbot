# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import cgi


def format_affil(characterName, corporationName, allianceName,
                 factionName, corp_ticker, alliance_ticker):
    """Represent character or structure data in a common format."""
    reply = ("<strong>{}</strong> is part of ".format(characterName)
             if characterName else "The structure is owned by ")

    reply += "corporation <strong>{} {}</strong>".format(
            corporationName, cgi.escape(format_tickers(corp_ticker, None))
    )

    if allianceName:
        reply += " in <strong>{} {}</strong>".format(
            allianceName, cgi.escape(format_tickers(None, alliance_ticker))
        )

    if factionName:
        reply += " which is part of the <strong>{}</strong>".format(factionName)

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


def disambiguate(given, like, category):
    """Disambiguate a list of names from the same category."""
    reply = 'Other {} like "{}": {}'.format(category, given, ", ".join(like[:3]))
    if len(like) > 3:
        reply += ", and {} others".format(len(like) - 3)

    return reply
