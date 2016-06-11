# coding: utf-8

from . import jabberbot


def botcmd(*args, **kwargs):
    """Mark decorated function as bot command."""

    def decorate(func, force_pm=False, **kwargs):
        setattr(func, "_vmbot_forcepm", force_pm)
        return jabberbot.botcmd(func, **kwargs)

    if args:
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)
