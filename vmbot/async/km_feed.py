# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
from datetime import datetime
import threading
import Queue

from ..helpers.exceptions import APIError
from ..helpers import api
from ..helpers import staticdata
from ..helpers.format import format_tickers
from ..models import ISK

KM_MIN_VAL = 5000000
REDISQ_URL = "https://redisq.zkillboard.com/listen.php"
FEED_FMT = ("{} {} | {} | {:.2f} ISK | {} ({}) | "
            "{:%Y-%m-%d %H:%M:%S} | https://zkillboard.com/kill/{}/")
KILL_SPOOL = 30 * 60
KILL_FMT = "{} new kill(s) worth {:.2f} ISK: https://zkillboard.com/corporation/{}/kills/"


class KMFeed(object):
    """Continuously fetch and process zKB lossmails."""

    class KM(object):
        """Store zKB killmail data."""

        def __init__(self, data):
            km, zkb = data['killmail'], data['zkb']
            victim = km['victim']
            system = staticdata.solarSystemData(km['solarSystem']['id'])

            self.id, self.value = km['killmail_id'], ISK(zkb['totalValue'])
            self.name = api.get_name(victim.get('character_id', victim['corporation_id']))
            self.tickers = api.get_tickers(victim['corporation_id'],
                                           victim.get('alliance_id', None))
            self.ship = staticdata.typeName(victim['ship_type_id'])
            self.system, self.region = system['solarSystemName'], system['regionName']
            self.time = datetime.strptime(km['killmail_time'], "%Y-%m-%dT%H:%M:%SZ")

        def format(self):
            return FEED_FMT.format(self.name, format_tickers(*self.tickers), self.ship,
                                   self.value, self.system, self.region, self.time, self.id)

    def __init__(self, corp_id):
        self.corp_id = corp_id
        self.kills = 0
        self.kill_value = 0
        self.kill_timer = None

        self.kill_lock = threading.Lock()
        self.loss_queue = Queue.Queue()

        self.abort_exec = threading.Event()
        self.worker = threading.Thread(target=self._request)
        self.worker.daemon = True
        self.worker.start()

    def close(self):
        self.abort_exec.set()
        self.worker.join()

    def process(self):
        return self.process_kills(), self.process_losses()

    def process_losses(self):
        losses = []
        try:
            while True:
                losses.append(self.loss_queue.get_nowait())
                self.loss_queue.task_done()
        except Queue.Empty:
            pass

        if not losses:
            return

        return ("{} new loss(es):\n".format(len(losses)) +
                '\n'.join(loss.format() for loss in losses))

    def process_kills(self):
        with self.kill_lock:
            if (self.kills == 0 or self.kill_value < KM_MIN_VAL or
                    (self.kill_timer and self.kill_timer > time.time())):
                return

            res = KILL_FMT.format(self.kills, ISK(self.kill_value), self.corp_id)
            self.kills = 0
            self.kill_value = 0
            self.kill_timer = None

            return res

    def _request(self):
        while not self.abort_exec.is_set():
            try:
                res = api.request_rest(REDISQ_URL, timeout=15)['package']
            except APIError:
                continue

            if res is not None:
                if (res['killmail']['victim']['corporation_id'] == self.corp_id
                        and res['zkb']['totalValue'] >= KM_MIN_VAL):
                    self.loss_queue.put(KMFeed.KM(res))
                elif any(att['corporation_id'] == self.corp_id
                         for att in res['killmail']['attackers'] if 'corporation_id' in att):
                    with self.kill_lock:
                        self.kills += 1
                        self.kill_value += res['zkb']['totalValue']
                        self.kill_timer = self.kill_timer or time.time() + KILL_SPOOL
