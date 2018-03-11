# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from sqlalchemy import (create_engine, Column, Integer, BigInteger, Float, String,
                        Text, Enum, DateTime, LargeBinary, PickleType, ForeignKey)
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy import and_, or_, func

from .files import BOT_DB

engine = create_engine("sqlite:///" + BOT_DB)
Session = sessionmaker(bind=engine)
Model = declarative_base()


def init_db(bind=engine):
    """Create all required database tables."""
    # Import all models which have associated tables
    from ..models import cache, message, note, user, wallet
    Model.metadata.create_all(bind)
