# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import signal
from functools import wraps

from .exceptions import TimeoutError
from . import database as db
from ..models.user import User

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


def generate_role_attr_map(user):
    return {'director': user.allow_director, 'admin': user.allow_admin, 'token': user.allow_token}


ROLE_ATTR_MAP = generate_role_attr_map(User)


def requires_role(role):
    if role not in ROLE_ATTR_MAP:
        raise ValueError("Invalid role name")

    def decorate(func):
        @wraps(func)
        def check_role(self, mess, args, **kwargs):
            jid = self.get_uname_from_mess(mess, full_jid=True).getStripped()
            sess = kwargs.get('session', None) or db.Session()

            allow = sess.query(ROLE_ATTR_MAP[role]).filter_by(jid=jid).scalar()
            if 'session' not in kwargs:
                sess.close()

            if allow:
                return func(self, mess, args, **kwargs)

        return check_role

    return decorate


def requires_dir_chat(func):
    @wraps(func)
    def check_dir_chat(self, mess, args, **kwargs):
        if mess.getFrom().getStripped() in config.JABBER['director_chatrooms']:
            return func(self, mess, args, **kwargs)

    return check_dir_chat


def requires_muc(func):
    @wraps(func)
    def check_muc(self, mess, args, **kwargs):
        if mess.getType() == b"groupchat":
            return func(self, mess, args, **kwargs)

    return check_muc


def inject_db(func):
    @wraps(func)
    def pass_db(*args, **kwargs):
        sess = db.Session()
        res = func(*args, session=sess, **kwargs)
        sess.close()

        return res

    return pass_db
