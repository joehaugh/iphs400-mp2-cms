"""Post data access. Scoping lives here, never only in templates.

An Editor's queries are always filtered to their own School, so another
School's Post is simply absent (None). An Admin sees every School.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

STATUSES = ("draft", "published")

# Fixed paths of the public site that a Post address must not collide with.
RESERVED_SLUGS = frozenset({
    "index", "schools", "posts", "pages", "style", "admin", "login", "logout", "new",
})


class PostError(ValueError):
    """A problem the user can fix; the message is shown as written."""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scope(user) -> tuple[str, tuple]:
    if user["role"] == "admin":
        return "", ()
    return " AND posts.school_id = ?", (user["school_id"],)


def list_posts(db: sqlite3.Connection, user, school_id: int | None = None) -> list[sqlite3.Row]:
    """`school_id` narrows an Admin's list; an Editor is always held to their own School."""
    clause, params = _scope(user)
    if school_id is not None and user["role"] == "admin":
        clause, params = " AND posts.school_id = ?", (school_id,)
    return db.execute(
        "SELECT posts.*, schools.short_name AS school_name FROM posts"
        " JOIN schools ON schools.id = posts.school_id"
        f" WHERE 1 = 1{clause} ORDER BY posts.updated_at DESC, posts.id DESC", params).fetchall()


def get_post(db: sqlite3.Connection, user, post_id: int) -> sqlite3.Row | None:
    clause, params = _scope(user)
    return db.execute(
        f"SELECT posts.* FROM posts WHERE posts.id = ?{clause}", (post_id, *params)).fetchone()


def list_schools(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute("SELECT id, name FROM schools ORDER BY is_network DESC, name").fetchall()


def target_school_id(db: sqlite3.Connection, user, chosen: str, noun: str = "Post") -> int:
    """The Editor's own School; for an Admin, the School they explicitly chose."""
    if user["role"] != "admin":
        return user["school_id"]
    if chosen.isdigit() and db.execute(
            "SELECT 1 FROM schools WHERE id = ?", (int(chosen),)).fetchone():
        return int(chosen)
    raise PostError(f"Choose which School this {noun} belongs to.")


def _clean(title: str, status: str) -> tuple[str, str]:
    title = title.strip()
    if not title:
        raise PostError("Give the Post a title.")
    if status not in STATUSES:
        raise PostError("Status must be draft or published.")
    return title, status


def _free_slug(db, school_id: int, wanted: str) -> str:
    slug = slugify(wanted)
    if not slug:
        raise PostError("The address needs at least one letter or number.")
    if slug in RESERVED_SLUGS:
        raise PostError(f"The address “{slug}” is reserved for a fixed page of the "
                        "site. Please change the title or type a different address.")
    candidate, n = slug, 1
    while db.execute("SELECT 1 FROM posts WHERE school_id = ? AND slug = ?",
                     (school_id, candidate)).fetchone():
        n += 1
        candidate = f"{slug}-{n}"
    return candidate


def create_post(db, user, *, school_id: int, title: str, body: str, status: str,
                address: str) -> int:
    title, status = _clean(title, status)
    slug = _free_slug(db, school_id, address.strip() or title)
    now = _now()
    cur = db.execute(
        "INSERT INTO posts (school_id, title, slug, body, status, author_id, created_at,"
        " updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (school_id, title, slug, body, status, user["id"], now, now))
    db.commit()
    return cur.lastrowid


def update_post(db, post: sqlite3.Row, *, title: str, body: str, status: str) -> None:
    """The address is fixed at creation: renaming it would break links to a live Post."""
    title, status = _clean(title, status)
    db.execute("UPDATE posts SET title = ?, body = ?, status = ?, updated_at = ?"
               " WHERE id = ?", (title, body, status, _now(), post["id"]))
    db.commit()


def set_draft(db, post: sqlite3.Row) -> None:
    """Unpublish a Post: it leaves the public site at the next Publish."""
    if post["status"] == "draft":
        return  # nothing to withdraw; don't count it as a change
    db.execute("UPDATE posts SET status = 'draft', updated_at = ? WHERE id = ?",
               (_now(), post["id"]))
    db.commit()


def can_delete(user, post: sqlite3.Row) -> bool:
    """Drafts may go for Editor or Admin; only the Admin removes published content."""
    return user["role"] == "admin" or post["status"] == "draft"


def delete_post(db, post: sqlite3.Row) -> None:
    db.execute("DELETE FROM posts WHERE id = ?", (post["id"],))
    db.commit()
