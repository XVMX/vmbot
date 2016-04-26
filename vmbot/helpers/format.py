def formatTickers(corporationTicker, allianceTicker):
    "Format ticker(s) like the EVE client does."
    ticker = ""
    if corporationTicker:
        ticker += "[{}] ".format(corporationTicker)
    if allianceTicker:
        # Wrapped in <span></span> to force XHTML parsing
        ticker += "<span>&lt;{}&gt;</span> ".format(allianceTicker)
    return ticker[:-1]
