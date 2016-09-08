# coding: utf-8

from . import jabberbot


def botcmd(f=None, **kwargs):
    """Mark decorated function as bot command."""
    def decorate(func, force_pm=False, **kwargs):
        setattr(func, "_vmbot_forcepm", force_pm)
        return jabberbot.botcmd(func, **kwargs)

    if f is not None:
        return decorate(f, **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)
