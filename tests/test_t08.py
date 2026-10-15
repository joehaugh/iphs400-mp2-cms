"""T08: end-to-end proof of the hard constraints across the whole site."""
import re
from urllib.parse import urljoin
from urllib.parse import urlsplit

from app.main import create_app
from app.publish import publish
from tests.test_t02 import create, post_row
from tests.test_t05 import make, network_page, page_row

EXTERNAL_HOSTS = {"img.example.org", "example.org"}  # the only other sites the tests link to
EVIL = ('Hello <script>alert("xss")</script> <img src="https://img.example.org/a.png" '
        'onerror="alert(2)"> <b onclick="steal()">bold</b> [click](javascript:alert(3)) '
        '<iframe src="https://evil.example.net"></iframe><style>body{display:none}</style>'
        '<svg onload="alert(4)"></svg>')


def test_seed_loads_sixty_made_up_schools_and_the_network_school(db):
    rows = db.execute("SELECT * FROM schools WHERE is_network = 0").fetchall()
    assert len(rows) == 60
    assert all(r["city"] and len(r["state"]) == 2 for r in rows)
    assert len({r["url_name"] for r in rows}) == 60
    assert db.execute("SELECT COUNT(*) FROM schools WHERE is_network = 1").fetchone()[0] == 1


def test_public_site_lists_all_sixty_schools(db, tmp_path):
    out = publish(db, tmp_path / "site")
    page = (out / "schools.html").read_text()
    names = [r["name"] for r in db.execute("SELECT name FROM schools WHERE is_network = 0")]
    assert len(names) == 60 and all(name in page for name in names)


def write_drafts_of_every_kind(client_as, csrf, db):
    editor, other, admin = client_as("editor"), client_as("editor_b"), client_as("admin")
    create(editor, csrf, title="Marker draft post", body="MARKER-POST-BODY")
    make(editor, csrf, title="Marker draft page", body="MARKER-PAGE-BODY")
    make(other, csrf, title="Marker other draft page", body="MARKER-OTHER-BODY")
    network_page(admin, csrf, db, "Marker draft network page", body="MARKER-NET-BODY",
                 pin_order="1")
    create(editor, csrf, title="Marker withdrawn post", body="MARKER-WITHDRAWN", status="published")
    editor.post(f"/admin/posts/{post_row(db, 'Marker withdrawn post')['id']}/unpublish",
                data={"csrf_token": csrf(editor, "/admin/posts/new")})
    # One published item of each kind so the site is not empty.
    create(editor, csrf, title="Visible post", status="published")
    make(editor, csrf, title="Visible page", status="published")
    make(editor, csrf, title="Marker withdrawn page", status="published")
    editor.post(f"/admin/pages/{page_row(db, 'Marker withdrawn page')['id']}/unpublish",
                data={"csrf_token": csrf(editor, "/admin/pages/new")})
    network_page(admin, csrf, db, "Visible network page", status="published", pin_order="2")


def test_no_draft_of_any_kind_appears_anywhere_in_the_output(client_as, csrf, db, tmp_path):
    write_drafts_of_every_kind(client_as, csrf, db)
    out = publish(db, tmp_path / "site")
    everything = "".join(p.read_text() for p in out.rglob("*") if p.is_file())
    assert "Visible post" in everything and "Visible network page" in everything
    assert "marker" not in everything.lower()
    for slug in ("marker-draft-post", "marker-draft-page", "marker-withdrawn-post", "marker-withdrawn-page",
                 "marker-draft-network-page", "marker-other-draft-page"):
        assert not list(out.rglob(f"{slug}*")), slug


def test_every_href_and_src_in_the_whole_site_is_relative_and_resolves(
        client_as, csrf, db, tmp_path):
    write_drafts_of_every_kind(client_as, csrf, db)
    create(client_as("editor"), csrf, title="With image", status="published",
           body="![pic](https://img.example.org/a.png) and [site](https://example.org/x)")
    out = publish(db, tmp_path / "site")
    checked = 0
    for page in out.rglob("*.html"):
        for ref in re.findall(r'(?:href|src)="([^"]*)"', page.read_text()):
            checked += 1
            if re.match(r"https?://", ref):
                assert urlsplit(ref).hostname in EXTERNAL_HOSTS, f"{page}: absolute own link {ref}"
                continue  # links to other sites are allowed; the site's own must be relative
            assert not ref.startswith("/"), f"{page}: {ref}"
            assert (page.parent / ref).resolve().exists(), f"{page}: broken {ref}"
    assert checked > 100  # 60 Schools plus content: the loop really ran


def assert_clean(html):
    # markdown-it leaves a javascript: "link" as inert escaped text, so check for a live href.
    assert "<script" not in html and 'alert("xss")' not in html and "alert(2)" not in html
    assert "onerror" not in html and "onclick" not in html and "steal(" not in html
    assert "<iframe" not in html and "<style" not in html and "onload" not in html
    assert "alert(4)" not in html
    assert not re.search(r'(?:href|src)="\s*javascript:', html, re.I)


def test_scripts_and_event_handlers_are_stripped_in_preview_and_output(
        client_as, csrf, db, tmp_path):
    e = client_as("editor")
    form = {"title": "Evil", "body": EVIL, "status": "published"}
    new_post = e.post("/admin/posts/preview", data={**form, "csrf_token": csrf(e, "/admin/posts/new")})
    new_page = e.post("/admin/pages/preview", data={**form, "csrf_token": csrf(e, "/admin/pages/new")})
    assert "Hello" in new_post.text and "Hello" in new_page.text
    create(e, csrf, title="Evil Post", body=EVIL, status="published")
    make(e, csrf, title="Evil Page", body=EVIL, status="published")
    pid, gid = post_row(db, "Evil Post")["id"], page_row(db, "Evil Page")["id"]
    saved_post = e.post(f"/admin/posts/{pid}/preview", data={**form, "csrf_token": csrf(e, "/admin/posts/new")})
    saved_page = e.post(f"/admin/pages/{gid}/preview", data={**form, "csrf_token": csrf(e, "/admin/pages/new")})
    for response in (new_post, new_page, saved_post, saved_page):
        body = response.text.split("<h2>Preview</h2>")[1]
        assert_clean(body)
    out = publish(db, tmp_path / "site")
    for path in ("st-ignatius/posts/evil-post.html", "st-ignatius/pages/evil-page.html"):
        html = (out / path).read_text()
        assert "Hello" in html
        assert_clean(html)
        assert 'src="https://img.example.org/a.png"' in html  # external images survive


# --- CSRF across every state-changing form -------------------------------------------

def post_routes():
    """Every POST route in the app, with path parameters filled in."""
    schema = create_app().openapi()["paths"]
    paths = {re.sub(r"\{[^}]+\}", "1", path) for path, ops in schema.items() if "post" in ops}
    assert len(paths) >= 15, "route discovery found too little"
    return sorted(paths)


def test_every_post_route_rejects_a_request_without_a_csrf_token(client_as, db):
    admin = client_as("admin")
    for path in post_routes():
        response = admin.post(path, follow_redirects=False)
        assert response.status_code == 403 and "CSRF" in response.text, (
            f"{path} answered {response.status_code} without a token")


def test_every_post_route_rejects_a_wrong_csrf_token(client_as, db):
    admin = client_as("admin")
    for path in post_routes():
        response = admin.post(path, data={"csrf_token": "forged"}, follow_redirects=False)
        assert response.status_code == 403 and "CSRF" in response.text, path


def console_pages(db):
    uid = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
    return ["/admin", "/admin/posts", "/admin/posts/new", "/admin/pages", "/admin/pages/new",
            "/admin/content", "/admin/users", "/admin/users/new", f"/admin/users/{uid}/edit",
            "/login", "/change-password"]


def test_every_form_that_posts_carries_a_csrf_token_on_every_console_page(client_as, csrf, db):
    admin, editor = client_as("admin"), client_as("editor")
    create(editor, csrf, title="Live", status="published")
    create(editor, csrf, title="Scrap")
    make(editor, csrf, title="Live Page", status="published")
    pages = console_pages(db) + [
        f"/admin/posts/{r['id']}/edit" for r in db.execute("SELECT id FROM posts")] + [
        f"/admin/pages/{r['id']}/edit" for r in db.execute("SELECT id FROM pages")]
    forms_seen = 0
    for client in (admin, editor):
        for path in pages:
            html = client.get(path).text
            for attrs, inner in re.findall(r"<form([^>]*)>(.*?)</form>", html, re.S):
                if 'method="get"' in attrs:
                    continue
                forms_seen += 1
                assert 'method="post"' in attrs, f"{path}: form without method=post: {attrs}"
                assert 'name="csrf_token"' in inner, f"{path}: form {attrs} lacks a CSRF token"
    assert forms_seen > 30


def test_every_link_on_every_console_page_leads_somewhere(client_as, csrf, db):
    """The console's links are relative (no href starts with "/"); each must still resolve."""
    editor, admin = client_as("editor"), client_as("admin")
    create(editor, csrf, title="Live", status="published")
    make(editor, csrf, title="Live Page", status="published")
    pages = console_pages(db) + [
        f"/admin/posts/{r['id']}/edit" for r in db.execute("SELECT id FROM posts")] + [
        f"/admin/pages/{r['id']}/edit" for r in db.execute("SELECT id FROM pages")] + [
        "/admin/users?x=1", "/admin/content?status=draft"]
    followed = 0
    for path in pages:
        html = admin.get(path).text
        for ref in re.findall(r'<a [^>]*href="([^"]*)"', html):
            assert not ref.startswith("/"), f"{path}: root-absolute link {ref}"
            target = urljoin(f"http://testserver{path}", ref)
            response = admin.get(target, follow_redirects=False)
            assert response.status_code == 200, f"{path} -> {ref} resolved to {target}: {response.status_code}"
            followed += 1
    assert followed > 40
