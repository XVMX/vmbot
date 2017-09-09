# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import signal
from functools import wraps

from .exceptions import TimeoutError
from . import database as db

import config


def timeout(seconds, error_message="Timer expired"):
    """Raise TimeoutError after timer expires."""
    def decorate(func):
        def handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, handle_timeout)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)

            return result

        return wrapper

    return decorate


def requires_dir(func):
    @wraps(func)
    def check_dir(self, mess, args):
        if self.get_uname_from_mess(mess) in config.DIRECTORS:
            return func(self, mess, args)

    return check_dir


def requires_admin(func):
    @wraps(func)
    def check_admin(self, mess, args):
        if self.get_uname_from_mess(mess) in config.ADMINS:
            return func(self, mess, args)

    return check_admin


def requires_dir_chat(func):
    @wraps(func)
    def check_dir_chat(self, mess, args):
        if mess.getFrom().getStripped() in config.JABBER['director_chatrooms']:
            return func(self, mess, args)

    return check_dir_chat


def inject_db(func):
    @wraps(func)
    def pass_db(*args, **kwargs):
        sess = db.Session()
        res = func(*args, session=sess, **kwargs)
        sess.close()

        return res

    return pass_db
