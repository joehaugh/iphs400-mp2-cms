"""Dashboard counts and the combined content list. Scoping lives here, not in templates.

An Editor's numbers and rows come only from their own School. "Changed" means
created, edited, or set back to draft since the last Publish started (all of it, if
Publish has never run). Drafts count, and deleted items leave no row to count.
"""
from __future__ import annotations

import sqlite3

from app import pages, posts
from app.publish import last_publish

KINDS = ("post", "page")


def _school_counts(db: sqlite3.Connection, user, since: str | None) -> list[dict]:
    clause, params = ("", ()) if user["role"] == "admin" else (
        " WHERE schools.id = ?", (user["school_id"],))
    rows = db.execute(
        "SELECT id, name, is_network FROM schools" + clause + " ORDER BY is_network DESC, name",
        params).fetchall()
    out = {r["id"]: {"id": r["id"], "name": r["name"], "is_network": r["is_network"],
                     "posts_draft": 0, "posts_published": 0,
                     "pages_draft": 0, "pages_published": 0, "changed": 0} for r in rows}
    for table in ("posts", "pages"):
        for r in db.execute(
                f"SELECT school_id, status, COUNT(*) AS n,"
                f" SUM(CASE WHEN ? IS NULL OR updated_at >= ? THEN 1 ELSE 0 END) AS changed"
                f" FROM {table} GROUP BY school_id, status", (since, since)):
            if r["school_id"] in out:
                out[r["school_id"]][f"{table}_{r['status']}"] = r["n"]
                out[r["school_id"]]["changed"] += r["changed"]
    return list(out.values())


def summary(db: sqlite3.Connection, user) -> dict:
    """Totals for the User's scope plus, for the Admin, one row per School."""
    rows = _school_counts(db, user, last_publish(db))
    keys = ("posts_draft", "posts_published", "pages_draft", "pages_published", "changed")
    return {"totals": {k: sum(r[k] for r in rows) for k in keys},
            "by_school": rows if user["role"] == "admin" else []}


def content_list(db: sqlite3.Connection, user, *, status: str = "", kind: str = "",
                 school_id: int | None = None) -> list[dict]:
    """Posts and Pages together, newest change first. Unknown filter values mean no filter."""
    kind = kind if kind in KINDS else ""
    items = []
    if kind in ("", "post"):
        items += [{"kind": "post", **dict(r)} for r in posts.list_posts(db, user, school_id)]
    if kind in ("", "page"):
        items += [{"kind": "page", **dict(r)} for r in pages.list_pages(db, user, school_id)]
    if status in posts.STATUSES:
        items = [i for i in items if i["status"] == status]
    return sorted(items, key=lambda i: (i["updated_at"], i["id"]), reverse=True)
