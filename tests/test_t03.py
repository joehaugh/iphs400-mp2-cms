"""T03: Publish puts Posts on the public site (Publish seam + HTTP permission)."""
import re
from datetime import datetime

from app import settings
from app.publish import last_publish, publish


def add_post(db, school, title, slug, body="Body.", status="published", created="2026-01-01T00:00:00+00:00"):
    school_id = db.execute("SELECT id FROM schools WHERE url_name = ?", (school,)).fetchone()[0]
    author = db.execute("SELECT id FROM users WHERE role = 'admin'").fetchone()[0]
    db.execute(
        "INSERT INTO posts (school_id, title, slug, body, status, author_id, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (school_id, title, slug, body, status, author, created, created))
    db.commit()


def read(out, path):
    return (out / path).read_text()


def test_only_published_posts_reach_the_site(db, tmp_path):
    add_post(db, "st-ignatius", "Live News", "live-news")
    add_post(db, "st-ignatius", "Secret Draft", "secret-draft", status="draft")
    out = publish(db, tmp_path / "site")
    assert (out / "st-ignatius/posts/live-news.html").exists()
    assert not (out / "st-ignatius/posts/secret-draft.html").exists()
    everything = "".join(p.read_text() for p in out.rglob("*.html"))
    assert "Live News" in everything
    assert "Secret Draft" not in everything and "secret-draft" not in everything


def test_home_feed_is_newest_first_labelled_by_school_not_author(db, tmp_path):
    add_post(db, "st-ignatius", "Oldest", "oldest", created="2026-01-01T00:00:00+00:00")
    add_post(db, "loyola-riverton", "Newest", "newest", created="2026-03-01T00:00:00+00:00")
    add_post(db, "xavier-lakeside", "Middle", "middle", created="2026-02-01T00:00:00+00:00")
    html = read(publish(db, tmp_path / "site"), "index.html")
    assert html.index("Newest") < html.index("Middle") < html.index("Oldest")
    assert "Loyola Riverton" in html
    assert "admin@example.test" not in html


def test_schools_index_lists_every_school_as_plain_text(db, tmp_path):
    out = publish(db, tmp_path / "site")
    html = read(out, "schools.html")
    for name in ("St. Ignatius Preparatory School", "Loyola Academy of Riverton",
                 "Xavier High School of Lakeside", "Campion College Preparatory"):
        assert name in html
    assert "<a " not in re.sub(r"<nav.*?</nav>|<header.*?</header>", "", html, flags=re.S)


def test_school_page_lists_only_that_schools_published_posts(db, tmp_path):
    add_post(db, "st-ignatius", "Ours", "ours")
    add_post(db, "st-ignatius", "Our Draft", "our-draft", status="draft")
    add_post(db, "loyola-riverton", "Theirs", "theirs")
    out = publish(db, tmp_path / "site")
    html = read(out, "st-ignatius/index.html")
    assert "Ours" in html and "posts/ours.html" in html
    assert "Theirs" not in html and "Our Draft" not in html


def test_site_links_are_all_relative_and_resolve(db, tmp_path):
    add_post(db, "st-ignatius", "Ours", "ours", body="![pic](https://img.example.org/a.png)")
    out = publish(db, tmp_path / "site")
    for page in out.rglob("*.html"):
        for ref in re.findall(r'(?:href|src)="([^"]*)"', page.read_text()):
            if ref.startswith("https://img.example.org"):
                continue
            assert not ref.startswith("/"), f"{page}: {ref}"
            assert (page.parent / ref).resolve().exists(), f"{page}: broken {ref}"


def test_markdown_is_sanitized_but_external_images_are_kept(db, tmp_path):
    body = ('Hi <script>alert(1)</script><b onclick="x()">bold</b>\n\n'
            '![pic](https://img.example.org/a.png)')
    add_post(db, "st-ignatius", "Ours", "ours", body=body)
    html = read(publish(db, tmp_path / "site"), "st-ignatius/posts/ours.html")
    assert "<script" not in html and "onclick" not in html and "alert(1)" not in html
    assert 'src="https://img.example.org/a.png"' in html


def test_publish_rebuilds_from_scratch(db, tmp_path):
    add_post(db, "st-ignatius", "Going", "going")
    out = publish(db, tmp_path / "site")
    (out / "stale.txt").write_text("old")
    db.execute("UPDATE posts SET status = 'draft'")
    db.commit()
    publish(db, out)
    assert not (out / "stale.txt").exists()
    assert not (out / "st-ignatius/posts/going.html").exists()
    assert "Going" not in read(out, "index.html")


def test_time_of_last_publish_is_recorded(db, tmp_path):
    assert last_publish(db) is None
    publish(db, tmp_path / "site")
    assert isinstance(datetime.fromisoformat(last_publish(db)), datetime)


def test_admin_runs_publish_from_the_console(client_as, csrf, db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    add_post(db, "st-ignatius", "Ours", "ours")
    c = client_as("admin")
    response = c.post("/admin/publish", data={"csrf_token": csrf(c, "/admin")},
                      follow_redirects=False)
    assert response.status_code == 303
    assert (tmp_path / "site/st-ignatius/posts/ours.html").exists()
    assert last_publish(db) is not None


def test_editor_cannot_publish(client_as, csrf, db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    c = client_as("editor")
    response = c.post("/admin/publish", data={"csrf_token": csrf(c, "/admin")},
                      follow_redirects=False)
    assert response.status_code == 403
    assert not (tmp_path / "site").exists()
    assert last_publish(db) is None
