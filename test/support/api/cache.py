# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from cachecontrol.cache import BaseCache


class MockFileCache(BaseCache):
    def __init__(
        self,
        directory,
        forever=False,
        filemode=0o0600,
        dirmode=0o0700,
        use_dir_lock=None,
        lock_class=None,
    ):
        pass

    def get(self, key):
        return None

    def set(self, key, value):
        pass

    def delete(self, key):
        pass
