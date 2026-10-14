"""T02: Editors write Posts for their own School (HTTP seam)."""
import re


def school_id(db, url_name):
    return db.execute("SELECT id FROM schools WHERE url_name = ?", (url_name,)).fetchone()[0]


def create(c, csrf, title="Hello Alumni", body="Some **news**.", status="draft",
           address="", **extra):
    data = {"title": title, "body": body, "status": status, "address": address,
            "csrf_token": csrf(c, "/admin/posts/new"), **extra}
    return c.post("/admin/posts", data=data, follow_redirects=False)


def post_row(db, title):
    return db.execute("SELECT * FROM posts WHERE title = ?", (title,)).fetchone()


def test_editor_creates_a_post_with_author_and_timestamps(client_as, csrf, db):
    c = client_as("editor")
    response = create(c, csrf, status="published")
    assert response.status_code == 303
    row = post_row(db, "Hello Alumni")
    assert row["school_id"] == school_id(db, "st-ignatius")
    assert row["status"] == "published" and row["slug"] == "hello-alumni"
    assert row["body"] == "Some **news**."
    author = db.execute("SELECT email FROM users WHERE id = ?", (row["author_id"],)).fetchone()
    assert author["email"] == "editor@example.test"
    assert row["created_at"] and row["updated_at"]


def test_editor_cannot_choose_the_school(client_as, csrf, db):
    c = client_as("editor")
    create(c, csrf, school_id=str(school_id(db, "loyola-riverton")))
    assert post_row(db, "Hello Alumni")["school_id"] == school_id(db, "st-ignatius")


def test_duplicate_title_gets_the_next_free_address(client_as, csrf, db):
    c = client_as("editor")
    create(c, csrf, title="Same Title")
    create(c, csrf, title="Same Title")
    create(c, csrf, title="Same Title")
    slugs = [r[0] for r in db.execute("SELECT slug FROM posts ORDER BY id")]
    assert slugs == ["same-title", "same-title-2", "same-title-3"]


def test_reserved_address_is_refused_in_plain_language(client_as, csrf, db):
    c = client_as("editor")
    response = create(c, csrf, title="Schools")
    assert response.status_code == 400
    assert "reserved" in response.text.lower()
    assert db.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    assert create(c, csrf, title="Fine", address="index").status_code == 400


def test_same_slug_may_exist_in_two_schools(client_as, csrf, db):
    create(client_as("editor"), csrf, title="Open House")
    create(client_as("editor_b"), csrf, title="Open House")
    rows = db.execute("SELECT slug FROM posts").fetchall()
    assert [r[0] for r in rows] == ["open-house", "open-house"]


def test_title_is_required_and_status_must_be_known(client_as, csrf):
    c = client_as("editor")
    assert create(c, csrf, title="   ").status_code == 400
    assert create(c, csrf, title="X", status="live").status_code == 400


def test_editor_list_shows_only_own_school_drafts_included(client_as, csrf):
    a, b = client_as("editor"), client_as("editor_b")
    create(a, csrf, title="Mine Draft")
    create(a, csrf, title="Mine Live", status="published")
    create(b, csrf, title="Theirs Secret")
    page = a.get("/admin/posts").text
    assert "Mine Draft" in page and "Mine Live" in page
    assert "Theirs Secret" not in page


def test_other_schools_post_is_not_found_to_view_edit_or_update(client_as, csrf, db):
    create(client_as("editor_b"), csrf, title="Theirs")
    pid = post_row(db, "Theirs")["id"]
    a = client_as("editor")
    assert a.get(f"/admin/posts/{pid}/edit").status_code == 404
    token = csrf(a, "/admin/posts/new")
    data = {"title": "Hijack", "body": "x", "status": "published", "csrf_token": token}
    assert a.post(f"/admin/posts/{pid}", data=data).status_code == 404
    assert a.post(f"/admin/posts/{pid}/preview", data=data).status_code == 404
    assert post_row(db, "Theirs")["status"] == "draft"
    assert a.get("/admin/posts/99999/edit").status_code == 404  # same as nonexistent


def test_editing_a_published_post_changes_it_in_place(client_as, csrf, db):
    c = client_as("editor")
    create(c, csrf, title="Original", status="published")
    row = post_row(db, "Original")
    response = c.post(f"/admin/posts/{row['id']}", follow_redirects=False,
                      data={"title": "Original", "body": "Fixed typo", "status": "published",
                            "address": row["slug"],
                            "csrf_token": csrf(c, f"/admin/posts/{row['id']}/edit")})
    assert response.status_code == 303
    after = post_row(db, "Original")
    assert after["id"] == row["id"] and after["body"] == "Fixed typo"
    assert after["status"] == "published" and after["slug"] == row["slug"]
    assert db.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 1


def test_editing_never_renames_the_address(client_as, csrf, db):
    c = client_as("editor")
    create(c, csrf, title="Stable")
    row = post_row(db, "Stable")
    c.post(f"/admin/posts/{row['id']}", data={
        "title": "Stable renamed", "body": "", "status": "draft", "address": "other",
        "csrf_token": csrf(c, f"/admin/posts/{row['id']}/edit")})
    assert db.execute("SELECT slug FROM posts WHERE id = ?", (row["id"],)).fetchone()[0] == "stable"


def test_preview_renders_sanitized_markdown(client_as, csrf):
    c = client_as("editor")
    body = ('# Big\n\n**bold** <script>alert(1)</script>\n\n'
            '<img src="https://example.org/p.jpg" onerror="alert(2)">\n\n'
            '<a href="javascript:alert(3)" onclick="x()">link</a>')
    response = c.post("/admin/posts/preview", data={
        "title": "T", "body": body, "status": "draft",
        "csrf_token": csrf(c, "/admin/posts/new")})
    assert response.status_code == 200
    html = response.text.split("<h2>Preview</h2>")[1]  # the textarea echoes the source
    assert "<h1>Big</h1>" in html and "<strong>bold</strong>" in html
    assert 'src="https://example.org/p.jpg"' in html  # external images allowed
    for bad in ("<script>alert", "onerror", "onclick", "javascript:"):
        assert bad not in html


def test_admin_creates_and_edits_for_any_school_choosing_explicitly(client_as, csrf, db):
    c = client_as("admin")
    target = school_id(db, "loyola-riverton")
    assert create(c, csrf, title="From Admin", school_id=str(target)).status_code == 303
    row = post_row(db, "From Admin")
    assert row["school_id"] == target
    assert "From Admin" in c.get("/admin/posts").text
    edited = c.post(f"/admin/posts/{row['id']}", follow_redirects=False, data={
        "title": "From Admin", "body": "edited", "status": "published", "address": row["slug"],
        "csrf_token": csrf(c, f"/admin/posts/{row['id']}/edit")})
    assert edited.status_code == 303 and post_row(db, "From Admin")["body"] == "edited"
    # the owning Editor sees it too
    assert "From Admin" in client_as("editor_b").get("/admin/posts").text


def test_admin_must_name_a_real_school(client_as, csrf, db):
    c = client_as("admin")
    assert create(c, csrf, title="No School").status_code == 400
    assert create(c, csrf, title="Bad School", school_id="9999").status_code == 400
    assert db.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0


def test_editor_cannot_write_to_the_network_school(client_as, csrf, db):
    # the School comes from the signed-in User, never the form
    c = client_as("editor")
    create(c, csrf, school_id=str(school_id(db, "network")))
    assert post_row(db, "Hello Alumni")["school_id"] != school_id(db, "network")


def test_post_forms_carry_csrf_and_reject_forgeries(client_as, csrf, db):
    c = client_as("editor")
    assert re.search(r'name="csrf_token"', c.get("/admin/posts/new").text)
    forged = c.post("/admin/posts", data={"title": "x", "body": "", "status": "draft"})
    assert forged.status_code == 403
    assert c.post("/admin/posts/preview", data={"title": "x"}).status_code == 403


def test_visitors_are_sent_to_sign_in(client):
    assert client.get("/admin/posts", follow_redirects=False).status_code == 303
