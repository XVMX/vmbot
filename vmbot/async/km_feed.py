# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import time
from datetime import datetime
import threading
import logging
import Queue

import numpy as np
from sklearn.neighbors import LocalOutlierFactor

from ..helpers.exceptions import APIError
from ..helpers import api
from ..helpers import staticdata
from ..helpers.format import format_tickers
from ..models import ISK

REDISQ_URL = "https://redisq.zkillboard.com/listen.php"
KM_MIN_VAL = 5000000
LOSS_FMT = ("{} {} | {} | {:.2f} ISK | {} ({}) | "
            "{:%Y-%m-%d %H:%M:%S} | https://zkillboard.com/kill/{}/")
KILL_SPOOL = 60 * 60
KILL_MAX_HL = 3
KILL_MAX_ANOM = 5
KILL_NUM_NEIGHBORS = 5
KILL_FMT = '<a href="https://zkillboard.com/kill/{}/">{:.2f} ISK {} ({})</a>'


def detect_anomalies(kills):
    num_neighbors = min(KILL_NUM_NEIGHBORS, len(kills) - 1)
    contam = min(float(KILL_MAX_ANOM) / len(kills), 0.2)
    lof = LocalOutlierFactor(num_neighbors, metric="manhattan", contamination=contam)

    kill_vals = np.array([[k.value / 1e6] for k in kills])
    res = lof.fit_predict(kill_vals)

    return [kills[i] for i in np.where(res == -1)]


class Killmail(object):
    """Store a zKB killmail."""

    def __init__(self, data):
        km = data['killmail']
        victim = km['victim']

        self.id, self.value = km['killmail_id'], ISK(data['zkb']['totalValue'])
        self._tickers = victim['corporation_id'], victim.get('alliance_id', None)
        self._ship = victim['ship_type_id']

    @property
    def tickers(self):
        if not isinstance(self._tickers[0], unicode):
            self._tickers = api.get_tickers(*self._tickers)
        return self._tickers

    @property
    def ship(self):
        if not isinstance(self._ship, unicode):
            self._ship = staticdata.type_name(self._ship)
        return self._ship

    def __unicode__(self):
        return KILL_FMT.format(self.id, self.value, self.ship,
                               format_tickers(*self.tickers, html=True))


class Lossmail(object):
    """Store a zKB lossmail."""

    def __init__(self, data):
        km = data['killmail']
        victim = km['victim']
        system = staticdata.system_data(km['solar_system_id'])

        self.id, self.value = km['killmail_id'], ISK(data['zkb']['totalValue'])
        self.name = api.get_name(victim.get('character_id', victim['corporation_id']))
        self.tickers = api.get_tickers(victim['corporation_id'], victim.get('alliance_id', None))
        self.ship = staticdata.type_name(victim['ship_type_id'])
        self.system, self.region = system['system_name'], system['region_name']
        self.time = datetime.strptime(km['killmail_time'], "%Y-%m-%dT%H:%M:%SZ")

    def __unicode__(self):
        return LOSS_FMT.format(self.name, format_tickers(*self.tickers), self.ship,
                               self.value, self.system, self.region, self.time, self.id)


class KMFeed(object):
    """Continuously fetch and process zKB killmails."""

    def __init__(self, corp_id):
        self.corp_id = corp_id
        self.kill_list = []
        self.kill_timer = None
        self.kill_lock = threading.Lock()
        self.loss_queue = Queue.Queue()

        self.abort_exec = threading.Event()
        self.worker = threading.Thread(target=self._async_exec)
        self.worker.daemon = True
        self.worker.start()

    def close(self):
        self.abort_exec.set()
        self.worker.join()

    def process(self):
        return self.process_kills(), self.process_losses()

    def process_kills(self):
        with self.kill_lock:
            if not self.kill_timer or self.kill_timer > time.time() or not self.kill_list:
                return

            kill_sum = sum(k.value for k in self.kill_list)
            res = "{} new kill(s) worth {:.2f} ISK: https://zkillboard.com/corporation/{}/"
            res = res.format(len(self.kill_list), ISK(kill_sum), self.corp_id)

            self.kill_list.sort(key=lambda k: k.value)
            suff_val_idx = next((i for i, k in enumerate(self.kill_list)
                                 if k.value >= KM_MIN_VAL), None)
            del self.kill_list[:suff_val_idx]

            if len(self.kill_list) <= 3:
                highlights = self.kill_list
            elif len(self.kill_list) <= 5:
                return res
            else:
                highlights = detect_anomalies(self.kill_list)

            self.kill_list = []
            self.kill_timer = None

        highlights = [unicode(k) for k, _ in zip(reversed(highlights), xrange(KILL_MAX_HL))]
        if highlights:
            res += "\nHighlight(s): " + ", ".join(highlights)

        return res

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

        return "{} new loss(es):\n".format(len(losses)) + '\n'.join(map(unicode, losses))

    def _async_exec(self):
        try:
            self._request()
        except Exception:
            logging.getLogger(__name__).exception("An error happened in KMFeed:")

    def _request(self):
        while not self.abort_exec.is_set():
            try:
                res = api.request_api(REDISQ_URL, timeout=15).json()['package']
            except APIError:
                continue
            if res is None:
                continue

            if (res['killmail']['victim']['corporation_id'] == self.corp_id
                    and res['zkb']['totalValue'] >= KM_MIN_VAL):
                self.loss_queue.put(Lossmail(res))
            elif any(att['corporation_id'] == self.corp_id
                     for att in res['killmail']['attackers'] if 'corporation_id' in att):
                with self.kill_lock:
                    self.kill_list.append(Killmail(res))
                    self.kill_timer = self.kill_timer or time.time() + KILL_SPOOL
