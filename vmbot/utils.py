# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta
import urllib

from concurrent import futures

from .botcmd import botcmd
from .helpers.exceptions import APIError, APIStatusError
from .helpers.time import ISO8601_DATETIME_FMT
from .helpers import api
from .helpers import staticdata
from .helpers.format import format_affil, format_tickers

import config


class EVEUtils(object):
    @botcmd
    def character(self, mess, args):
        """<character> - Employment information for a single character"""
        args = args.strip()
        if not args:
            return "Please provide a character name"

        token = self.get_token()
        if "esi-search.search_structures.v1" not in token.scopes:
            return "SSO token is missing a required scope"

        params = {'search': args, 'categories': "character", 'strict': "true"}
        try:
            res = token.request_esi("/v3/characters/{}/search/",
                                    (token.character_id,), params=params)
            char_id = res['character'][0]
        except APIError as e:
            return unicode(e)
        except KeyError:
            return "This EVE character doesn't exist"

        # Process ESI lookups in parallel
        sheet_fut = self.api_pool.submit(api.request_esi, "/v5/characters/{}/", (char_id,))
        try:
            corp_hist = api.request_esi("/v2/characters/{}/corporationhistory/", (char_id,))
        except APIError:
            corp_hist = []

        # Process corporation history
        num_recs = len(corp_hist)
        corp_hist.sort(key=lambda x: x['record_id'])
        for i in reversed(xrange(num_recs)):
            rec = corp_hist[i]
            rec['start_date'] = datetime.strptime(rec['start_date'], ISO8601_DATETIME_FMT)
            rec['end_date'] = corp_hist[i + 1]['start_date'] if i + 1 < num_recs else None

        # Show entries from the last 5 years (min 10, max 25)
        min_age = datetime.utcnow() - timedelta(days=5 * 365)
        max_hist = max(-25, -len(corp_hist))
        while max_hist < -10 and corp_hist[max_hist]['end_date'] <= min_age:
            max_hist += 1
        corp_hist = corp_hist[max_hist:]

        # Load character sheet
        try:
            sheet = sheet_fut.result()
        except APIError as e:
            return unicode(e)

        # Load corporation data
        corp_ids = {sheet['corporation_id']}
        corp_ids.update(rec['corporation_id'] for rec in corp_hist)

        corp_futs = []
        hist_futs = []
        for id_ in corp_ids:
            f = self.api_pool.submit(api.request_esi, "/v5/corporations/{}/", (id_,))
            f.req_id = id_
            corp_futs.append(f)

            f = self.api_pool.submit(api.request_esi, "/v3/corporations/{}/alliancehistory/",
                                     (id_,))
            f.req_id = id_
            hist_futs.append(f)

        corps = {}
        for f in futures.as_completed(corp_futs):
            try:
                corps[f.req_id] = f.result()
            except APIError:
                corps[f.req_id] = {'name': "ERROR", 'ticker': "ERROR"}

        ally_hist = {}
        for f in futures.as_completed(hist_futs):
            try:
                ally_hist[f.req_id] = f.result()
                ally_hist[f.req_id].sort(key=lambda x: x['record_id'])
            except APIError:
                ally_hist[f.req_id] = []

        # Corporation Alliance history
        ally_ids = {sheet['alliance_id']} if 'alliance_id' in sheet else set()
        for rec in corp_hist:
            hist = ally_hist[rec['corporation_id']]
            date_hist = [datetime.strptime(ally['start_date'], ISO8601_DATETIME_FMT)
                         for ally in hist]
            start_date = rec['start_date']
            end_date = rec['end_date'] or datetime.utcnow()

            j, k = 0, len(date_hist) - 1
            while j <= k:
                if date_hist[j] <= start_date:
                    j += 1
                elif date_hist[k] >= end_date:
                    k -= 1
                else:
                    break
            j = max(0, j - 1)
            k += 1

            rec['alliances'] = [ent['alliance_id'] for ent in hist[j:k] if 'alliance_id' in ent]
            ally_ids.update(rec['alliances'])

        # Load alliance data
        ally_futs = []
        for id_ in ally_ids:
            f = self.api_pool.submit(api.request_esi, "/v4/alliances/{}/", (id_,))
            f.req_id = id_
            ally_futs.append(f)

        allys = {}
        for f in futures.as_completed(ally_futs):
            try:
                allys[f.req_id] = f.result()
            except APIError:
                allys[f.req_id] = {'name': "ERROR", 'ticker': "ERROR"}

        # Format output
        corp = corps[sheet['corporation_id']]
        birthday = datetime.strptime(sheet['birthday'], ISO8601_DATETIME_FMT)
        ally = allys[sheet['alliance_id']] if 'alliance_id' in sheet else {}
        fac_name = staticdata.faction_name(sheet['faction_id']) if 'faction_id' in sheet else None

        reply = format_affil(sheet['name'], sheet.get('security_status', 0.0), birthday,
                             corp['name'], ally.get('name', None), fac_name, corp['ticker'],
                             ally.get('ticker', None))

        for rec in corp_hist:
            end = ("{:%Y-%m-%d %H:%M:%S}".format(rec['end_date'])
                   if rec['end_date'] is not None else "now")
            corp = corps[rec['corporation_id']]
            ally_ticker = "</strong>/<strong>".join(
                format_tickers(None, allys[id_]['ticker'], html=True) for id_ in rec['alliances']
            )
            ally_ticker = " " + ally_ticker if ally_ticker else ""

            reply += "<br />From {:%Y-%m-%d %H:%M:%S} til {} in <strong>{} {}{}</strong>".format(
                rec['start_date'], end, corp['name'],
                format_tickers(corp['ticker'], None, html=True), ally_ticker
            )

        if len(corp_hist) < num_recs:
            reply += ("<br />The full history is available at "
                      "https://evewho.com/character/{}").format(char_id)

        return reply

    @botcmd
    def evetime(self, mess, args):
        """Current EVE time and server status"""
        reply = "The current EVE time is {:%Y-%m-%d %H:%M:%S}".format(datetime.utcnow())

        try:
            stat = api.request_esi("/v2/status/")
        except APIStatusError:
            reply += ". The server is offline."
        except APIError:
            pass
        else:
            reply += ". The server is online"
            if stat.get('vip', False):
                reply += " (VIP mode)"
            reply += " with {:,} players.".format(stat['players'])

        return reply

    @botcmd(disable_if=not config.BLACKLIST_URL)
    def rcbl(self, mess, args):
        """<character>[, ...] - Query blacklist status of character(s)"""
        results = []
        for character in (item.strip() for item in args.split(',')):
            try:
                res = api.request_api(config.BLACKLIST_URL + '/' + character).json()
            except APIError:
                results.append("Failed to load blacklist entry for " + character)
            else:
                results.append("{} is <strong>{}</strong>".format(character, res[0]['output']))

        return "<br />".join(results)
