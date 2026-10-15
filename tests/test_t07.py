"""T07: Dashboards and filters (HTTP seam)."""
import re
from urllib.parse import urljoin

from app.publish import publish
from tests.test_t02 import create
from tests.test_t05 import make, network_page


def cells(html, label):
    """The <td> values of the table row whose first cell is `label`."""
    row = re.search(rf"<tr><t[hd]>{re.escape(label)}</t[hd]>(.*?)</tr>", html, re.S)
    assert row, f"no row {label!r}"
    return [int(v) for v in re.findall(r"<td>(\d+)</td>", row.group(1))]


def changed(html):
    return int(re.search(r"last Publish: <strong>(\d+)</strong>", html).group(1))


def seed_content(client_as, csrf):
    a, b = client_as("editor"), client_as("editor_b")
    create(a, csrf, title="A draft post")
    create(a, csrf, title="A live post", status="published")
    make(a, csrf, title="A live page", status="published")
    create(b, csrf, title="B draft post")
    make(b, csrf, title="B draft page")
    make(b, csrf, title="B other page")
    return a, b


def test_editor_dashboard_counts_only_their_school(client_as, csrf):
    a, _ = seed_content(client_as, csrf)
    html = a.get("/admin").text
    assert cells(html, "Posts") == [1, 1] and cells(html, "Pages") == [0, 1]
    assert "By School" not in html


def test_admin_dashboard_has_network_totals_and_a_per_school_breakdown(client_as, csrf, db):
    seed_content(client_as, csrf)
    network_page(client_as("admin"), csrf, db, "About", status="published")
    html = client_as("admin").get("/admin").text
    assert cells(html, "Posts") == [2, 1] and cells(html, "Pages") == [2, 2]
    assert cells(html, "St. Ignatius Preparatory School") == [1, 1, 0, 1, 3]
    assert cells(html, "Loyola Academy of Riverton") == [1, 0, 2, 0, 3]
    assert cells(html, "Xavier High School of Lakeside") == [0, 0, 0, 0, 0]  # not posting
    assert cells(html, "Jesuit Schools Network") == [0, 0, 0, 1, 1]


def test_changed_since_last_publish_counts_edits_and_resets_on_publish(
        client_as, csrf, db, tmp_path):
    a, _ = seed_content(client_as, csrf)
    assert changed(a.get("/admin").text) == 3       # never published: everything
    assert changed(client_as("admin").get("/admin").text) == 6
    publish(db, tmp_path / "site")
    db.execute("UPDATE posts SET updated_at = '2000-01-01T00:00:00+00:00'")
    db.execute("UPDATE pages SET updated_at = '2000-01-01T00:00:00+00:00'")
    db.commit()
    assert changed(a.get("/admin").text) == 0
    pid = db.execute("SELECT id FROM posts WHERE title = 'A live post'").fetchone()[0]
    a.post(f"/admin/posts/{pid}/unpublish", data={"csrf_token": csrf(a, "/admin/posts/new")})
    db.execute("UPDATE posts SET updated_at = '2999-01-01T00:00:00+00:00' WHERE id = ?", (pid,))
    db.commit()
    assert changed(a.get("/admin").text) == 1
    assert changed(client_as("editor_b").get("/admin").text) == 0  # not their School's change


def titles(html):
    return re.findall(r'/edit">([^<]+)</a>', html)


def test_content_list_filters_by_status_and_type(client_as, csrf):
    a, _ = seed_content(client_as, csrf)
    assert sorted(titles(a.get("/admin/content").text)) == [
        "A draft post", "A live page", "A live post"]
    assert titles(a.get("/admin/content?status=draft").text) == ["A draft post"]
    assert sorted(titles(a.get("/admin/content?status=published").text)) == [
        "A live page", "A live post"]
    assert titles(a.get("/admin/content?type=page").text) == ["A live page"]
    assert titles(a.get("/admin/content?type=post&status=published").text) == ["A live post"]
    assert len(titles(a.get("/admin/content?status=nonsense&type=junk").text)) == 3


def test_content_links_open_the_right_editor(client_as, csrf, db):
    a, _ = seed_content(client_as, csrf)
    html = a.get("/admin/content").text
    links = re.findall(r'href="([^"]*/edit)"', html)
    assert len(links) == 3  # the Editor's two Posts and one Page
    for link in links:
        path = urljoin("http://testserver/admin/content", link)  # resolve like a browser
        assert a.get(path).status_code == 200, path


def test_editor_never_sees_other_schools_content_in_list_or_filters(client_as, csrf, db):
    a, _ = seed_content(client_as, csrf)
    other = db.execute("SELECT id FROM schools WHERE url_name = 'loyola-riverton'").fetchone()[0]
    for query in ("", "?status=draft", "?type=page", f"?school={other}"):
        page = a.get(f"/admin/content{query}").text
        assert "B draft" not in page and "B other" not in page, query
        assert 'name="school"' not in page
    assert "B draft post" in client_as("admin").get("/admin/content").text


def test_admin_filters_content_by_school(client_as, csrf, db):
    seed_content(client_as, csrf)
    other = db.execute("SELECT id FROM schools WHERE url_name = 'loyola-riverton'").fetchone()[0]
    page = client_as("admin").get(f"/admin/content?school={other}&type=page").text
    assert sorted(titles(page)) == ["B draft page", "B other page"]
    assert client_as("admin").get("/admin/content?school=%C2%B2").status_code == 200


def test_content_list_needs_sign_in(client):
    assert client.get("/admin/content", follow_redirects=False).status_code == 303


def test_an_edit_made_as_publish_started_still_counts_as_changed(client_as, csrf, db, tmp_path):
    a, _ = seed_content(client_as, csrf)
    publish(db, tmp_path / "site")
    stamp = db.execute("SELECT value FROM meta WHERE key = 'last_publish'").fetchone()[0]
    db.execute("UPDATE posts SET updated_at = '2000-01-01T00:00:00+00:00'")
    db.execute("UPDATE pages SET updated_at = '2000-01-01T00:00:00+00:00'")
    db.execute("UPDATE posts SET updated_at = ? WHERE title = 'A live post'", (stamp,))
    db.commit()
    assert changed(a.get("/admin").text) == 1
