# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from datetime import timedelta

from concurrent.futures import ThreadPoolExecutor

from vmbot.helpers import database as db
from vmbot.helpers.exceptions import APIStatusError
from vmbot.models.market import MarketStructure

from vmbot.services.marketcache import MarketStructureLookup


def mock_status_error(status_code):
    exc = mock.Mock(name="RequestException")
    exc.response.status_code = status_code
    return APIStatusError(exc, "TestException")


MAIN_SYSTEM_ID = 30004759  # 1DQ1-A
OTHER_SYSTEM_ID = 30000144  # Perimeter
MARKET_TYPE_ID = 35833  # Fortizar
NOMARKET_TYPE_ID = 35832  # Astrahus
MOCK_STRUCTURES = {
    6834936: {
        "name": "test 1",
        "owner_id": 109299958,
        "solar_system_id": MAIN_SYSTEM_ID,
        "type_id": MARKET_TYPE_ID
    },
    38357831: {
        "name": "test 2",
        "owner_id": 109299958,
        "solar_system_id": MAIN_SYSTEM_ID,
        "type_id": MARKET_TYPE_ID,
        "has_market": False
    },
    89904839: {
        "name": "test 3",
        "owner_id": 109299958,
        "solar_system_id": OTHER_SYSTEM_ID,
        "type_id": MARKET_TYPE_ID
    },
    9895031: {
        "name": "test 4",
        "owner_id": 109299958,
        "solar_system_id": MAIN_SYSTEM_ID,
        "type_id": NOMARKET_TYPE_ID
    },
    1978391: {
        "name": "test 5",
        "owner_id": 109299958,
        "solar_system_id": OTHER_SYSTEM_ID,
        "type_id": NOMARKET_TYPE_ID
    },
    3968928: mock_status_error(403)
}
VALID_IDS_CACHED = {6834936}
VALID_IDS_FRESH = VALID_IDS_CACHED | {38357831}


def mock_request_esi(route, fmt=(), *args, **kwargs):
    assert route.endswith("/universe/structures/{}/")
    res = MOCK_STRUCTURES[fmt[0]]

    if isinstance(res, Exception):
        raise res
    return res


class TestMarketStructureLookup(unittest.TestCase):
    db_engine = db.create_engine("sqlite://")

    @classmethod
    def setUpClass(cls):
        db.init_db(cls.db_engine)
        db.Session.configure(bind=cls.db_engine)

    @classmethod
    def tearDownClass(cls):
        db.Session.configure(bind=db.engine)
        cls.db_engine.dispose()
        del cls.db_engine

    def setUp(self):
        self.sess = db.Session()
        self.api_pool = ThreadPoolExecutor(max_workers=2)
        self.token = mock.Mock(name="SSOToken")
        self.token.request_esi.side_effect = mock_request_esi

        with self.sess.begin():
            self.sess.execute(db.delete(MarketStructure))

    def tearDown(self):
        del self.api_pool
        self.sess.close()

    def test_cache(self):
        lookup = MarketStructureLookup(self.api_pool, self.token)
        ids = lookup(MAIN_SYSTEM_ID, list(MOCK_STRUCTURES))

        self.assertSetEqual(ids, VALID_IDS_FRESH)
        for id_, spec in MOCK_STRUCTURES.items():
            if not isinstance(spec, Exception) and not spec.get("has_market", True):
                lookup.mark_inaccessible(id_)
        lookup.finalize()

        lookup = MarketStructureLookup(self.api_pool, self.token)
        ids = lookup(MAIN_SYSTEM_ID, list(MOCK_STRUCTURES))
        self.assertSetEqual(ids, VALID_IDS_CACHED)
        lookup.finalize()

    def test_expired_cache(self):
        # Seed cache with expired entries
        with self.sess.begin():
            for id_, spec in MOCK_STRUCTURES.items():
                if isinstance(spec, Exception):
                    s = MarketStructure.from_esi_denied(id_)
                else:
                    s = MarketStructure.from_esi_result(id_, spec)
                    s.has_market = spec.get("has_market", True)

                s.last_updated -= MarketStructureLookup.MARKET_CACHE_TTL + timedelta(days=1)
                self.sess.add(s)

        lookup = MarketStructureLookup(self.api_pool, self.token)
        ids = lookup(MAIN_SYSTEM_ID, list(MOCK_STRUCTURES))
        self.assertSetEqual(ids, VALID_IDS_FRESH)
        lookup.finalize()

        # Verify last_updated has been adjusted
        q = db.select(MarketStructure).where(MarketStructure.structure_id.in_(VALID_IDS_FRESH))
        for s in self.sess.execute(q).scalars():
            self.assertLessEqual(s.update_age, timedelta(hours=1))

    def test_esi_error(self):
        self.token.request_esi.side_effect = mock_status_error(500)
        lookup = MarketStructureLookup(self.api_pool, self.token)

        self.assertRaises(APIStatusError, lookup, MAIN_SYSTEM_ID, list(MOCK_STRUCTURES))

    @mock.patch("sqlalchemy.orm.Session.commit",
                side_effect=db.OperationalError("", (), "TestException"))
    @mock.patch("sqlalchemy.orm.Session.rollback")
    def test_commit_error(self, mock_rollback, mock_commit):
        lookup = MarketStructureLookup(self.api_pool, self.token)
        lookup.finalize()
        mock_rollback.assert_called()


if __name__ == '__main__':
    unittest.main()
