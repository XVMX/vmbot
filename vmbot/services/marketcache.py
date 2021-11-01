# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from datetime import datetime, timedelta

from concurrent import futures

from ..helpers.exceptions import APIStatusError
from ..helpers import database as db
from ..helpers import staticdata
from ..models import MarketStructure


class MarketStructureLookup(object):
    """Filter a set of structure_ids to those that are potentially markets."""

    MARKET_CACHE_TTL = timedelta(days=3)

    def __init__(self, api_pool, token):
        self.sess = db.Session()
        self.pool = api_pool
        self.token = token

        self.markets = {}
        self.market_typeids = staticdata.market_structure_types()

    def _submit_lookup(self, struct):
        f = self.pool.submit(self.token.request_esi,
                             "/v2/universe/structures/{}/", (struct.structure_id,))
        f.req_struct = struct
        return f

    def _start_lookups(self, system_id, struct_ids):
        select_markets = (db.select(MarketStructure).
                          where(MarketStructure.structure_id.in_(struct_ids)))
        self.markets = {s.structure_id: s for s in self.sess.execute(select_markets).scalars()}

        struct_futs = []
        for id_ in struct_ids:
            s = self.markets.get(id_, None)
            if s is None:
                # Unknown structure; pretend access was denied previously
                s = MarketStructure.from_esi_denied(id_)
                self.sess.add(s)
                struct_futs.append(self._submit_lookup(s))
                continue

            if ((s.type_id is not None and s.type_id not in self.market_typeids)
                    or (s.system_id is not None and s.system_id != system_id)):
                del self.markets[id_]
                continue

            if s.update_age > self.MARKET_CACHE_TTL:
                if s.system_id is None:
                    # Access was denied on previous lookup, retry now
                    struct_futs.append(self._submit_lookup(s))
                    del self.markets[id_]
                else:
                    # Reattempt market access regardless of cached status
                    s.has_market = True

                # onupdate doesn't trigger when values are "updated" to their current values
                s.last_updated = datetime.utcnow()
            elif not s.has_market:
                del self.markets[id_]

        return struct_futs

    def _handle_lookup_result(self, f, system_id):
        try:
            result = f.result()
        except APIStatusError as e:
            if e.status_code != 403:
                raise e

            # Access is still denied
            return

        s = f.req_struct
        s.type_id = result.get('type_id', None)
        s.system_id = result['solar_system_id']
        s.has_market = True

        if ((s.type_id is not None and s.type_id not in self.market_typeids)
                or s.system_id != system_id):
            return

        self.markets[s.structure_id] = s

    def __call__(self, system_id, struct_ids):
        futs = self._start_lookups(system_id, struct_ids)
        for f in futures.as_completed(futs):
            self._handle_lookup_result(f, system_id)
        return set(self.markets.keys())

    def mark_inaccessible(self, struct_id):
        # struct_id must come from a __call__ to the same instance.
        # Otherwise, a KeyError from self.markets will be raised.
        self.markets[struct_id].has_market = False

    def finalize(self):
        try:
            self.sess.commit()
        except db.OperationalError:
            self.sess.rollback()
        self.sess.close()
