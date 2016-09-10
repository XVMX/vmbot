# coding: utf-8

import sys
import os

# Add directory with vmbot modules to path
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from vmbot.helpers import database as db

# Initialize database tables
db.init_db()
