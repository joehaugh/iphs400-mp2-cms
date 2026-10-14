"""Seed data: Schools, the Network School, an Admin, and Editors for two Schools.

The School rows are made-up placeholders; the real list of about 60 comes from
the client. Safe to run twice.
"""
from __future__ import annotations

import sqlite3

from app.passwords import hash_password

NETWORK_URL_NAME = "network"

SCHOOLS = [
    # name, short_name, city, state, url_name, is_network
    ("Jesuit Schools Network", "Network", "Washington", "DC", NETWORK_URL_NAME, 1),
    ("St. Ignatius Preparatory School", "St. Ignatius", "Springfield", "OH", "st-ignatius", 0),
    ("Loyola Academy of Riverton", "Loyola Riverton", "Riverton", "IL", "loyola-riverton", 0),
    ("Xavier High School of Lakeside", "Xavier Lakeside", "Lakeside", "MI", "xavier-lakeside", 0),
    ("Campion College Preparatory", "Campion", "Prairie Falls", "WI", "campion", 0),
]

# key -> (email, role, school url_name)
USERS = {
    "admin": ("admin@example.test", "admin", None),
    "editor": ("editor@example.test", "editor", "st-ignatius"),
    "editor_b": ("editor-b@example.test", "editor", "loyola-riverton"),
}


def seed(conn: sqlite3.Connection, passwords: dict[str, str]) -> None:
    """`passwords` maps the keys in USERS to a plain password (hashed here)."""
    for row in SCHOOLS:
        conn.execute(
            "INSERT OR IGNORE INTO schools (name, short_name, city, state, url_name, is_network)"
            " VALUES (?, ?, ?, ?, ?, ?)", row)
    for key, (email, role, school_url) in USERS.items():
        school = conn.execute(
            "SELECT id FROM schools WHERE url_name = ?", (school_url,)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO users (email, password_hash, role, school_id)"
            " VALUES (?, ?, ?, ?)",
            (email, hash_password(passwords[key]), role, school["id"] if school else None))
    conn.commit()
