# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from os import path
import io

DATADIR = path.abspath(path.join(path.dirname(__file__), "data"))


def open(file, *args, **kwargs):
    file = path.join(DATADIR, file)
    return io.open(file, *args, **kwargs)
