# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import threading
import Queue

from ..helpers.exceptions import APIError
from ..helpers import api
from ..helpers import staticdata
from ..helpers.format import format_tickers
from ..models import ISK

KM_MIN_VAL = 5000000
REDISQ_URL = "https://redisq.zkillboard.com/listen.php"
FEED_FMT = "{} {} | {} | {:.2f} ISK | {} ({}) | {} | https://zkillboard.com/kill/{}/"


class KMFeed(object):
    """Continuously fetch and process zKB lossmails."""

    class KM(object):
        """Store zKB killmail data."""

        def __init__(self, data):
            km, zkb = data['killmail'], data['zkb']
            victim = km['victim']
            system = staticdata.solarSystemData(km['solarSystem']['id'])

            self.name = (victim['character']['name'] if 'character' in victim
                         else victim['corporation']['name'])
            self.tickers = api.get_tickers(
                victim['corporation']['id'],
                victim['alliance']['id'] if 'alliance' in victim else None
            )
            self.ship, self.value = victim['shipType']['name'], ISK(zkb['totalValue'])
            self.system, self.region = system['solarSystemName'], system['regionName']
            self.time, self.id = km['killTime'], km['killID']

        def format(self):
            return FEED_FMT.format(self.name, format_tickers(*self.tickers), self.ship,
                                   self.value, self.system, self.region, self.time, self.id)

    def __init__(self, corp_id):
        self.corp_id = corp_id
        self.queue = Queue.Queue()

        self.abort_exec = threading.Event()
        self.worker = threading.Thread(target=self._request)
        self.worker.daemon = True
        self.worker.start()

    def close(self):
        self.abort_exec.set()
        self.worker.join()

    def process(self):
        losses = []
        try:
            while True:
                losses.append(self.queue.get_nowait())
                self.queue.task_done()
        except Queue.Empty:
            pass

        if not losses:
            return

        return ("{} new loss(es):\n".format(len(losses)) +
                '\n'.join(loss.format() for loss in losses))

    def _request(self):
        while not self.abort_exec.is_set():
            try:
                res = api.request_rest(REDISQ_URL, timeout=15)['package']
            except APIError:
                continue

            if (res is not None and res['killmail']['victim']['corporation']['id'] == self.corp_id
                    and res['zkb']['totalValue'] >= KM_MIN_VAL):
                self.queue.put(KMFeed.KM(res))
