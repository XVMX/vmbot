# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import logging

from . import path
from . import news_feed
from . import evemail
from . import wallet_update

from vmbot.helpers.logging import setup_logging
from vmbot.helpers import database as db
from vmbot.helpers.sso import SSOToken

import config

FEEDS = (news_feed,)
ESI_UPDATES = (evemail, wallet_update)

if __name__ == "__main__":
    logger = setup_logging(logging.StreamHandler())
    session = db.Session()

    try:
        for feed in FEEDS:
            if feed.needs_run(session):
                feed.main(session)

        if any(update.needs_run(session) for update in ESI_UPDATES):
            token = SSOToken.from_refresh_token(config.SSO['refresh_token'])
            for update in ESI_UPDATES:
                if update.needs_run(session):
                    update.main(session, token)
    except Exception:
        logger.exception("An error happened in a cron module:")

    session.close()
    logging.shutdown()
