"""T05: Pages and navigation (HTTP seam, plus Publish for the output checks)."""
import re

from app.publish import publish
from tests.test_t02 import school_id


def make(c, csrf, title="About Us", body="Hello **page**.", status="draft", address="",
         **extra):
    data = {"title": title, "body": body, "status": status, "address": address,
            "csrf_token": csrf(c, "/admin/pages/new"), **extra}
    return c.post("/admin/pages", data=data, follow_redirects=False)


def page_row(db, title):
    return db.execute("SELECT * FROM pages WHERE title = ?", (title,)).fetchone()


def network_page(admin, csrf, db, title, **extra):
    return make(admin, csrf, title=title, school_id=str(school_id(db, "network")), **extra)


def act(c, csrf, pid, action):
    return c.post(f"/admin/pages/{pid}/{action}", follow_redirects=False,
                  data={"csrf_token": csrf(c, "/admin/pages/new")})


def test_editor_creates_edits_lists_and_deletes_a_draft_page(client_as, csrf, db):
    c = client_as("editor")
    assert make(c, csrf).status_code == 303
    row = page_row(db, "About Us")
    assert row["school_id"] == school_id(db, "st-ignatius") and row["slug"] == "about-us"
    assert "About Us" in c.get("/admin/pages").text
    data = {"title": "About Us 2", "body": "x", "status": "published",
            "csrf_token": csrf(c, f"/admin/pages/{row['id']}/edit")}
    assert c.post(f"/admin/pages/{row['id']}", data=data).status_code == 200  # follows redirect
    assert page_row(db, "About Us 2")["slug"] == "about-us"  # address stays fixed
    assert act(c, csrf, row["id"], "delete").status_code == 403  # published
    act(c, csrf, row["id"], "unpublish")
    assert act(c, csrf, row["id"], "delete").status_code == 303
    assert db.execute("SELECT COUNT(*) FROM pages").fetchone()[0] == 0


def test_page_address_rules_match_posts(client_as, csrf, db):
    c = client_as("editor")
    make(c, csrf)
    make(c, csrf)
    assert {r["slug"] for r in db.execute("SELECT slug FROM pages")} == {"about-us", "about-us-2"}
    refused = make(c, csrf, title="Schools")
    assert refused.status_code == 400 and "reserved" in refused.text


def test_a_post_and_a_page_may_share_an_address(client_as, csrf, db):
    c = client_as("editor")
    c.post("/admin/posts", data={"title": "Welcome", "csrf_token": csrf(c, "/admin/posts/new")})
    assert make(c, csrf, title="Welcome").status_code == 303
    assert page_row(db, "Welcome")["slug"] == "welcome"


def test_other_schools_page_is_not_found_on_every_route(client_as, csrf, db):
    make(client_as("editor_b"), csrf, title="Theirs", status="published")
    pid = page_row(db, "Theirs")["id"]
    a = client_as("editor")
    assert a.get(f"/admin/pages/{pid}/edit").status_code == 404
    for action in ("delete", "unpublish", "preview"):
        assert act(a, csrf, pid, action).status_code == 404
    data = {"title": "X", "body": "", "status": "draft", "csrf_token": csrf(a, "/admin/pages/new")}
    assert a.post(f"/admin/pages/{pid}", data=data).status_code == 404
    assert "Theirs" not in a.get("/admin/pages").text
    assert page_row(db, "Theirs")["status"] == "published"


def test_editor_cannot_see_or_write_network_pages(client_as, csrf, db):
    network_page(client_as("admin"), csrf, db, "About", status="published")
    pid = page_row(db, "About")["id"]
    e = client_as("editor")
    assert e.get(f"/admin/pages/{pid}/edit").status_code == 404
    assert "About" not in e.get("/admin/pages").text
    assert act(e, csrf, pid, "delete").status_code == 404
    make(e, csrf, title="Mine", school_id=str(school_id(db, "network")), pin_order="1")
    row = page_row(db, "Mine")
    assert row["school_id"] == school_id(db, "st-ignatius") and row["pin_order"] is None


def test_page_forms_need_csrf(client_as, csrf, db):
    c = client_as("editor")
    make(c, csrf)
    pid = page_row(db, "About Us")["id"]
    assert c.post("/admin/pages", data={"title": "x"}).status_code == 403
    assert c.post(f"/admin/pages/{pid}/delete").status_code == 403
    assert c.post(f"/admin/pages/{pid}/unpublish").status_code == 403


def test_admin_chooses_a_school_and_pins_only_network_pages(client_as, csrf, db):
    admin = client_as("admin")
    refused = make(admin, csrf, title="No School")
    assert refused.status_code == 400 and "this Page belongs" in refused.text
    make(admin, csrf, title="Ours", school_id=str(school_id(db, "st-ignatius")), pin_order="1")
    assert page_row(db, "Ours")["pin_order"] is None
    assert network_page(admin, csrf, db, "Join", pin_order="x").status_code == 400
    network_page(admin, csrf, db, "Join", pin_order="2")
    assert page_row(db, "Join")["pin_order"] == 2
    assert 'name="pin_order"' in admin.get(f"/admin/pages/{page_row(db, 'Join')['id']}/edit").text
    assert 'name="pin_order"' not in client_as("editor").get("/admin/pages/new").text


def test_publish_writes_pages_and_nav_lists_pinned_first_in_order(client_as, csrf, db, tmp_path):
    admin = client_as("admin")
    network_page(admin, csrf, db, "How to join", status="published", pin_order="2")
    network_page(admin, csrf, db, "About", status="published", pin_order="1")
    network_page(admin, csrf, db, "Unpinned", status="published")
    network_page(admin, csrf, db, "Hidden", status="draft", pin_order="0")
    e = client_as("editor")
    make(e, csrf, title="Zeta", status="published")
    make(e, csrf, title="Alpha", status="published")
    make(e, csrf, title="Secret", status="draft")
    out = publish(db, tmp_path / "site")
    assert (out / "network/pages/about.html").exists()
    assert (out / "st-ignatius/pages/zeta.html").exists()
    assert not (out / "st-ignatius/pages/secret.html").exists()
    for rel in ("index.html", "schools.html", "st-ignatius/index.html",
                "st-ignatius/pages/zeta.html"):
        nav = re.search(r"<nav>(.*?)</nav>", (out / rel).read_text(), re.S).group(1)
        titles = re.findall(r">([^<]+)</a>", nav)
        assert titles == ["About", "How to join", "Schools"], rel
        assert "Hidden" not in nav and "Unpinned" not in nav
    school = (out / "st-ignatius/index.html").read_text()
    assert school.index("Alpha") < school.index("Zeta") and "Secret" not in school
    assert "Hidden" not in "".join(p.read_text() for p in out.rglob("*.html"))


def test_unpublished_page_leaves_output_and_nav_at_next_publish(client_as, csrf, db, tmp_path):
    admin = client_as("admin")
    network_page(admin, csrf, db, "About", status="published", pin_order="1")
    make(client_as("editor"), csrf, title="Gone", status="published")
    out = publish(db, tmp_path / "site")
    assert "About" in (out / "index.html").read_text()
    act(admin, csrf, page_row(db, "About")["id"], "unpublish")
    act(admin, csrf, page_row(db, "Gone")["id"], "delete")
    out = publish(db, tmp_path / "site")
    assert not (out / "network/pages/about.html").exists()
    assert not (out / "st-ignatius/pages/gone.html").exists()
    assert "About" not in (out / "index.html").read_text()
    assert "Gone" not in (out / "st-ignatius/index.html").read_text()


def test_page_links_are_relative_and_resolve_and_markdown_is_sanitized(client_as, csrf, db, tmp_path):
    admin = client_as("admin")
    network_page(admin, csrf, db, "About", status="published", pin_order="1",
                 body="Hi <script>alert(1)</script>")
    make(client_as("editor"), csrf, title="Mine", status="published")
    out = publish(db, tmp_path / "site")
    assert "<script" not in (out / "network/pages/about.html").read_text()
    for page in out.rglob("*.html"):
        for ref in re.findall(r'(?:href|src)="([^"]*)"', page.read_text()):
            assert not ref.startswith("/"), f"{page}: {ref}"
            assert (page.parent / ref).resolve().exists(), f"{page}: broken {ref}"


def test_page_forms_submit_with_post_and_carry_a_csrf_token(client_as, csrf, db):
    c = client_as("editor")
    make(c, csrf, status="published")
    pid = page_row(db, "About Us")["id"]
    for path in ("/admin/pages/new", f"/admin/pages/{pid}/edit"):
        html = c.get(path).text
        forms = re.findall(r"<form([^>]*)>(.*?)</form>", html, re.S)
        for attrs, inner in forms[1:]:  # the first is Sign out
            assert 'method="post"' in attrs and 'name="csrf_token"' in inner, path
