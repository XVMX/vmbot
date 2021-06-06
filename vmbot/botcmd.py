# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from . import jabberbot


def botcmd(f=None, **kwargs):
    """Mark decorated function as bot command."""
    def decorate(func, disable_if=False, force_pm=False, **kwargs):
        if disable_if:
            return func

        setattr(func, "_vmbot_forcepm", force_pm)
        return jabberbot.botcmd(func, **kwargs)

    if f is not None:
        return decorate(f, **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)
