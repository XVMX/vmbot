# coding: utf-8

from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

from .files import BOT_DB

engine = create_engine("sqlite:///{}".format(BOT_DB))
Session = sessionmaker(bind=engine)
Model = declarative_base()


def init_db():
    Model.metadata.create_all(engine)
