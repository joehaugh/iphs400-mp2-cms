"""SQLite access. The path is read at call time so tests can point it elsewhere."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from app import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS schools (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    short_name  TEXT NOT NULL,
    city        TEXT NOT NULL,
    state       TEXT NOT NULL,
    url_name    TEXT NOT NULL UNIQUE,
    is_network  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    id                    INTEGER PRIMARY KEY,
    email                 TEXT NOT NULL UNIQUE,
    password_hash         TEXT NOT NULL,
    role                  TEXT NOT NULL CHECK (role IN ('admin', 'editor')),
    active                INTEGER NOT NULL DEFAULT 1,
    must_change_password  INTEGER NOT NULL DEFAULT 0,
    session_epoch         INTEGER NOT NULL DEFAULT 0,  -- bumped to void old cookies
    school_id             INTEGER REFERENCES schools(id),
    CHECK ((role = 'editor') = (school_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY,
    school_id   INTEGER NOT NULL REFERENCES schools(id),
    title       TEXT NOT NULL,
    slug        TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    author_id   INTEGER NOT NULL REFERENCES users(id),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    UNIQUE (school_id, slug)
);

CREATE TABLE IF NOT EXISTS meta (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    conn.executescript(SCHEMA)
    conn.commit()
    if own:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
