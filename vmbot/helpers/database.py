# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from sqlalchemy import (create_engine, event, Column, Boolean, Integer, BigInteger, Float,
                        String, Text, Enum, DateTime, LargeBinary, PickleType, ForeignKey)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy import and_, or_, func

import config

DB_URL = config.DB_URL
if not DB_URL or DB_URL.lower() in ("sqlite", "sqlite3", "builtin", "built-in"):
    from .files import BOT_DB
    DB_URL = "sqlite:///" + BOT_DB

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
Model = declarative_base()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.close()


def init_db(bind=engine):
    """Create all required database tables."""
    # Import all models which have associated tables
    from ..models import message, note, user, wallet
    Model.metadata.create_all(bind)
