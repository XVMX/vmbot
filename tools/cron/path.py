# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import sys
from os import path, pardir

# Add top directory with vmbot and config modules to path
VM_DIR = path.abspath(path.join(path.dirname(__file__), pardir, pardir))
if VM_DIR not in sys.path:
    sys.path.insert(1, VM_DIR)
