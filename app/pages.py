"""Page data access. Same scoping and address rules as Posts (see app/posts.py).

An Editor's queries are held to their own School, so another School's Page, and
every Network School Page, is simply absent (None). Only the Admin writes to
the Network School, and only the Admin pins Pages.
"""
from __future__ import annotations

import sqlite3

from app.posts import (RESERVED_SLUGS, STATUSES, PostError, _now, slugify,  # noqa: F401
                       can_delete, list_schools, target_school_id)


def _scope(user) -> tuple[str, tuple]:
    if user["role"] == "admin":
        return "", ()
    return " AND pages.school_id = ?", (user["school_id"],)


def list_pages(db: sqlite3.Connection, user, school_id: int | None = None) -> list[sqlite3.Row]:
    clause, params = _scope(user)
    if school_id is not None and user["role"] == "admin":
        clause, params = " AND pages.school_id = ?", (school_id,)
    return db.execute(
        "SELECT pages.*, schools.short_name AS school_name FROM pages"
        " JOIN schools ON schools.id = pages.school_id"
        f" WHERE 1 = 1{clause} ORDER BY pages.updated_at DESC, pages.id DESC", params).fetchall()


def get_page(db: sqlite3.Connection, user, page_id: int) -> sqlite3.Row | None:
    clause, params = _scope(user)
    return db.execute(
        f"SELECT pages.*, schools.is_network FROM pages"
        f" JOIN schools ON schools.id = pages.school_id WHERE pages.id = ?{clause}",
        (page_id, *params)).fetchone()


def _clean(title: str, status: str, pin: str, is_network: bool) -> tuple[str, str, int | None]:
    title = title.strip()
    if not title:
        raise PostError("Give the Page a title.")
    if status not in STATUSES:
        raise PostError("Status must be draft or published.")
    pin = pin.strip()
    if not is_network or not pin:
        return title, status, None  # only Network School Pages are pinned
    if not pin.isdigit():
        raise PostError("Pin order must be a whole number, or blank to leave the Page unpinned.")
    return title, status, int(pin)


def _free_slug(db, school_id: int, wanted: str) -> str:
    slug = slugify(wanted)
    if not slug:
        raise PostError("The address needs at least one letter or number.")
    if slug in RESERVED_SLUGS:
        raise PostError(f"The address “{slug}” is reserved for a fixed page of the "
                        "site. Please change the title or type a different address.")
    candidate, n = slug, 1
    while db.execute("SELECT 1 FROM pages WHERE school_id = ? AND slug = ?",
                     (school_id, candidate)).fetchone():
        n += 1
        candidate = f"{slug}-{n}"
    return candidate


def _is_network(db, school_id: int) -> bool:
    return bool(db.execute("SELECT is_network FROM schools WHERE id = ?",
                           (school_id,)).fetchone()["is_network"])


def create_page(db, user, *, school_id: int, title: str, body: str, status: str,
                address: str, pin_order: str = "") -> int:
    title, status, pin = _clean(title, status, pin_order, _is_network(db, school_id))
    slug = _free_slug(db, school_id, address.strip() or title)
    now = _now()
    cur = db.execute(
        "INSERT INTO pages (school_id, title, slug, body, status, pin_order, author_id,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (school_id, title, slug, body, status, pin, user["id"], now, now))
    db.commit()
    return cur.lastrowid


def update_page(db, page: sqlite3.Row, *, title: str, body: str, status: str,
                pin_order: str = "") -> None:
    """The address is fixed at creation: renaming it would break links to a live Page."""
    title, status, pin = _clean(title, status, pin_order, bool(page["is_network"]))
    db.execute("UPDATE pages SET title = ?, body = ?, status = ?, pin_order = ?,"
               " updated_at = ? WHERE id = ?", (title, body, status, pin, _now(), page["id"]))
    db.commit()


def set_draft(db, page: sqlite3.Row) -> None:
    if page["status"] == "draft":
        return
    db.execute("UPDATE pages SET status = 'draft', updated_at = ? WHERE id = ?",
               (_now(), page["id"]))
    db.commit()


def delete_page(db, page: sqlite3.Row) -> None:
    db.execute("DELETE FROM pages WHERE id = ?", (page["id"],))
    db.commit()
