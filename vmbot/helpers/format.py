# coding: utf-8


def format_tickers(corporation_ticker, alliance_ticker):
    """Format ticker(s) like the default EVE client does."""
    tickers = []

    if corporation_ticker:
        tickers.append("[{}]".format(corporation_ticker))
    if alliance_ticker:
        # Wrapped in <span></span> to force XHTML parsing
        tickers.append("<span>&lt;{}&gt;</span>".format(alliance_ticker))

    return ' '.join(tickers)


def disambiguate(given, like, category):
    """Disambiguate a list of names from the same category."""
    reply = u'Other {} like "{}": {}'.format(category, given, ", ".join(like[:3]))
    if len(like) > 3:
        reply += ", and {} others".format(len(like) - 3)

    return reply
