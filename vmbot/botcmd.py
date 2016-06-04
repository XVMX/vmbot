from . import jabberbot


def botcmd(*args, **kwargs):
    def decorate(func, forcePM=False, **kwargs):
        setattr(func, "_vmbot_forcepm", forcePM)
        return jabberbot.botcmd(func, **kwargs)

    if args:
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)
