# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import signal
from functools import wraps

from .exceptions import TimeoutError


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
