import time
import json
import sqlite3

from .files import CACHE_DB


_cache_version = 4


def __connect():
    """Connect to the cache database."""
    conn = sqlite3.connect(CACHE_DB)
    return conn


def __schema(conn):
    """Update the cache database schema."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS metadata (
             key TEXT NOT NULL PRIMARY KEY,
             value TEXT NOT NULL
           );"""
    )

    res = conn.execute(
        """SELECT value
           FROM metadata
           WHERE key = "version";"""
    ).fetchall()
    if res and int(res[0][0]) < _cache_version:
        conn.execute("DROP TABLE cache;")
    conn.commit()

    conn.execute(
        """INSERT OR REPLACE INTO metadata
           VALUES ("version", :version);""",
        {'version': _cache_version}
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cache (
             key TEXT NOT NULL PRIMARY KEY,
             value BLOB NOT NULL,
             expiry INTEGER NOT NULL
           );"""
    )
    conn.commit()


def _get(key):
    """Retrieve a cached buffer."""
    conn = __connect()

    try:
        res = conn.execute(
            """SELECT value
               FROM cache
               WHERE key = :key
                 AND expiry > :expiry;""",
            {'key': key, 'expiry': int(time.time())}
        ).fetchall()
    except:
        res = []

    conn.close()
    return res[0][0] if len(res) == 1 else None


def _set(key, value, expiry=None):
    """Add a buffer to the cache."""
    conn = __connect()
    __schema(conn)

    # 1h default expiry
    expiry = expiry or time.time() + 60 * 60
    conn.execute(
        """INSERT OR REPLACE INTO cache
           VALUES (:key, :value, :expiry);""",
        {'key': key, 'value': value, 'expiry': expiry}
    )
    conn.execute(
        """DELETE FROM cache
           WHERE expiry <= :expiry;""",
        {'expiry': int(time.time())}
    )
    conn.commit()

    conn.close()
    return True


def getHTTP(path, params=None):
    """Retrieve a cached HTTP request."""
    key = path + (json.dumps(params) if params else "")
    res = _get(key)
    return str(res) if res else res


def setHTTP(path, doc, expiry=None, params=None):
    """Add a HTTP request to the cache."""
    key = path + (json.dumps(params) if params else "")
    return _set(key, sqlite3.Binary(doc), expiry)
