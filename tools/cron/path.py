# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import sys
from os import path, pardir

# Add top directory with vmbot module to path
sys.path.insert(1, path.abspath(path.join(path.dirname(__file__), pardir, pardir)))
