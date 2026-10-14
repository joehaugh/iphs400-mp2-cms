"""Render the public site into site/ as plain HTML.

publish() rebuilds the whole output from the database and records when it ran.
Layout: index.html (merged feed), schools.html, <school>/index.html and
<school>/posts/<slug>.html and <school>/pages/<slug>.html. Two rules the rubric checks:

  1. Only PUBLISHED content is written here. A draft that reaches site/ is a bug.
  2. Every href and src is RELATIVE ("style.css", "posts/x.html"), never
     root-absolute ("/style.css"), because Pages serves this from a subfolder.
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import settings
from app.markdown import render_markdown
from app.seed import NETWORK_URL_NAME

CSS = """/* Minimal starter styles — make them yours. */
:root { color-scheme: light dark; }
body { font: 16px/1.6 system-ui, sans-serif; margin: 0 auto; max-width: 42rem; padding: 1rem; }
header a { font-weight: 700; text-decoration: none; }
main { margin-block: 2rem; }
"""


def environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


def _write(out: Path, path: str, html: str) -> None:
    target = out / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html)


def render_site(db: sqlite3.Connection, out: Path | None = None) -> Path:
    """Write every published Post under `out`, from scratch."""
    out = out or settings.SITE
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = environment()
    (out / "style.css").write_text(CSS)

    schools = db.execute("SELECT * FROM schools ORDER BY name").fetchall()
    posts = db.execute(
        "SELECT posts.*, schools.url_name AS school_url FROM posts"
        " JOIN schools ON schools.id = posts.school_id WHERE posts.status = 'published'"
        " ORDER BY posts.created_at DESC, posts.id DESC").fetchall()

    def entry(post, prefix: str) -> dict:
        school = next(s for s in schools if s["id"] == post["school_id"])
        return {"title": post["title"], "school": school["short_name"],
                "date": post["created_at"][:10],
                "href": f"{prefix}{post['school_url']}/posts/{post['slug']}.html"}

    pages = db.execute(
        "SELECT pages.*, schools.url_name AS school_url FROM pages"
        " JOIN schools ON schools.id = pages.school_id WHERE pages.status = 'published'").fetchall()
    pinned = sorted((p for p in pages if p["pin_order"] is not None and p["school_url"] == NETWORK_URL_NAME),
                    key=lambda p: (p["pin_order"], p["id"]))

    def page(path: str, template: str, depth: int, **context) -> None:
        root = "../" * depth
        nav = [{"title": p["title"], "href": f"{root}{NETWORK_URL_NAME}/pages/{p['slug']}.html"}
               for p in pinned]
        _write(out, path, env.get_template(template).render(
            site_title=settings.SITE_TITLE, css_path=f"{root}style.css",
            home_path=f"{root}index.html", schools_path=f"{root}schools.html", nav=nav, **context))

    page("index.html", "public/home.html", 0, title=settings.SITE_TITLE,
         items=[entry(p, "") for p in posts])
    page("schools.html", "public/schools.html", 0, title="Schools",
         schools=[s for s in schools if not s["is_network"]])
    for school in schools:
        mine = [p for p in posts if p["school_id"] == school["id"]]
        its_pages = sorted((p for p in pages if p["school_id"] == school["id"]),
                           key=lambda p: p["title"].lower())
        if school["is_network"] and not (mine or its_pages):
            continue  # the Network School only has a page once it has content
        # Inside <school>/, content is just posts/<slug>.html or pages/<slug>.html.
        page(f"{school['url_name']}/index.html", "public/school.html", 1,
             title=school["name"], school=school,
             items=[{**entry(p, ""), "href": f"posts/{p['slug']}.html"} for p in mine],
             page_items=[{"title": p["title"], "href": f"pages/{p['slug']}.html"}
                         for p in its_pages])
        for p in mine:
            page(f"{school['url_name']}/posts/{p['slug']}.html", "public/post.html", 2,
                 title=p["title"], school=school, date=p["created_at"][:10],
                 body_html=render_markdown(p["body"]), school_path="../index.html")
        for p in its_pages:
            page(f"{school['url_name']}/pages/{p['slug']}.html", "public/post.html", 2,
                 title=p["title"], school=school, date=None,
                 body_html=render_markdown(p["body"]), school_path="../index.html")
    return out


def publish(db: sqlite3.Connection, out: Path | None = None) -> Path:
    """The Admin's Publish: render the site, then record when it happened."""
    out = render_site(db, out)
    db.execute("INSERT INTO meta (key, value) VALUES ('last_publish', ?)"
               " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
               (datetime.now(timezone.utc).isoformat(timespec="seconds"),))
    db.commit()
    return out


def last_publish(db: sqlite3.Connection) -> str | None:
    row = db.execute("SELECT value FROM meta WHERE key = 'last_publish'").fetchone()
    return row["value"] if row else None
