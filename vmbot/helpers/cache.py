# coding: utf-8

from datetime import datetime, timedelta
import re
import json

from .exceptions import NoCacheError
from . import database as db


def parse_cache_control(cache_control):
    """Parse Cache-Control HTTP header."""
    cc_lower = cache_control.lower()
    if "no-cache" in cc_lower or "no-store" in cc_lower:
        raise NoCacheError

    try:
        return datetime.utcnow() + timedelta(seconds=int(
            re.search("max-age=(\d+)", cache_control, re.IGNORECASE).group(1)
        ))
    except AttributeError:
        raise NoCacheError


def parse_xml_cache(xml):
    """Parse EVE Online XML-API cache value."""
    try:
        return datetime.strptime(xml.find("cachedUntil").text, "%Y-%m-%d %H:%M:%S")
    except AttributeError:
        raise NoCacheError


class BaseCacheObject(db.Model):
    """Cache arbitrary data."""
    __tablename__ = "cache"

    key = db.Column(db.String, nullable=False, primary_key=True)
    value = db.Column(db.LargeBinary, nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)

    def __init__(self, key, value, expiry):
        self.key = key
        self.value = value
        self.expiry = expiry

        self.save()

    def save(self):
        """Save cache object to the database."""
        session = db.Session()
        session.merge(self)
        session.commit()
        session.close()

    @classmethod
    def get(cls, key, session):
        """Load cached data from the database."""
        cls.clear(session)

        res = session.query(cls).filter_by(key=key).first()
        return res.value if res is not None else None

    @classmethod
    def clear(cls, session):
        """Delete outdated cache objects from the database."""
        session.query(cls).filter(cls.expiry < datetime.utcnow()).delete()
        session.commit()


class HTTPCacheObject(BaseCacheObject):
    """Cache an HTTP response using URL and parameters as key."""

    def __init__(self, url, doc, expiry=None, params=None):
        url += json.dumps(params) if params else ""
        expiry = expiry or datetime.utcnow() + timedelta(hours=1)
        super(HTTPCacheObject, self).__init__(url, doc, expiry)

    @classmethod
    def get(cls, url, session, params=None):
        """Load cached HTTP response from the database."""
        url += json.dumps(params) if params else ""
        return super(HTTPCacheObject, cls).get(url, session)
