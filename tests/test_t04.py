"""T04: Unpublish and delete rules (HTTP seam, plus Publish for the output check)."""
from app.publish import publish
from tests.test_t02 import create, post_row, school_id


def act(c, csrf, pid, action):
    return c.post(f"/admin/posts/{pid}/{action}", follow_redirects=False,
                  data={"csrf_token": csrf(c, "/admin/posts/new")})


def count(db):
    return db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]


def test_editor_deletes_a_draft_of_their_school(client_as, csrf, db):
    c = client_as("editor")
    create(c, csrf, title="Scrap")
    assert act(c, csrf, post_row(db, "Scrap")["id"], "delete").status_code == 303
    assert count(db) == 0


def test_editor_cannot_delete_a_published_post_but_can_set_it_to_draft(client_as, csrf, db):
    c = client_as("editor")
    create(c, csrf, title="Live", status="published")
    pid = post_row(db, "Live")["id"]
    assert act(c, csrf, pid, "delete").status_code == 403
    assert post_row(db, "Live")["status"] == "published"
    assert act(c, csrf, pid, "unpublish").status_code == 303
    assert post_row(db, "Live")["status"] == "draft"


def test_admin_permanently_deletes_a_published_post(client_as, csrf, db):
    create(client_as("editor"), csrf, title="Live", status="published")
    assert act(client_as("admin"), csrf, post_row(db, "Live")["id"], "delete").status_code == 303
    assert count(db) == 0


def test_other_schools_post_is_not_found_to_delete_unpublish_or_set_status(client_as, csrf, db):
    create(client_as("editor_b"), csrf, title="Theirs", status="published")
    pid = post_row(db, "Theirs")["id"]
    a = client_as("editor")
    assert act(a, csrf, pid, "delete").status_code == 404
    assert act(a, csrf, pid, "unpublish").status_code == 404
    data = {"title": "Theirs", "body": "", "status": "draft",
            "csrf_token": csrf(a, "/admin/posts/new")}
    assert a.post(f"/admin/posts/{pid}", data=data).status_code == 404
    assert act(a, csrf, 99999, "delete").status_code == 404  # same as nonexistent
    assert post_row(db, "Theirs")["status"] == "published"


def test_unpublish_and_delete_forms_need_csrf(client_as, csrf, db):
    c = client_as("editor")
    create(c, csrf, title="Draft")
    pid = post_row(db, "Draft")["id"]
    assert c.post(f"/admin/posts/{pid}/delete").status_code == 403
    assert c.post(f"/admin/posts/{pid}/unpublish").status_code == 403
    assert count(db) == 1


def test_edit_page_offers_only_the_actions_the_user_may_take(client_as, csrf, db):
    e = client_as("editor")
    create(e, csrf, title="Live", status="published")
    create(e, csrf, title="Draft")
    live, draft = post_row(db, "Live")["id"], post_row(db, "Draft")["id"]
    page = e.get(f"/admin/posts/{live}/edit").text
    assert f"/admin/posts/{live}/unpublish" in page and f"/admin/posts/{live}/delete" not in page
    assert f"/admin/posts/{draft}/delete" in e.get(f"/admin/posts/{draft}/edit").text
    assert f"/admin/posts/{live}/delete" in client_as("admin").get(
        f"/admin/posts/{live}/edit").text


def test_after_publish_a_withdrawn_or_deleted_post_leaves_the_output(client_as, csrf, db, tmp_path):
    e = client_as("editor")
    create(e, csrf, title="Withdrawn", status="published")
    create(e, csrf, title="Removed", status="published")
    create(e, csrf, title="Stays", status="published")
    out = publish(db, tmp_path / "site")
    assert (out / "st-ignatius/posts/withdrawn.html").exists()
    act(e, csrf, post_row(db, "Withdrawn")["id"], "unpublish")
    act(client_as("admin"), csrf, post_row(db, "Removed")["id"], "delete")
    out = publish(db, tmp_path / "site")
    assert not (out / "st-ignatius/posts/withdrawn.html").exists()
    assert not (out / "st-ignatius/posts/removed.html").exists()
    assert (out / "st-ignatius/posts/stays.html").exists()
    everything = "".join(p.read_text() for p in out.rglob("*.html"))
    assert "Withdrawn" not in everything and "Removed" not in everything


def test_admin_filters_the_list_by_school_and_editor_has_no_filter(client_as, csrf, db):
    create(client_as("editor"), csrf, title="Ignatian News")
    create(client_as("editor_b"), csrf, title="Riverton News")
    admin = client_as("admin")
    both = admin.get("/admin/posts").text
    assert "Ignatian News" in both and "Riverton News" in both and 'name="school"' in both
    only = admin.get(f"/admin/posts?school={school_id(db, 'loyola-riverton')}").text
    assert "Riverton News" in only and "Ignatian News" not in only
    assert "Ignatian News" in admin.get("/admin/posts?school=abc").text  # junk = no filter
    e = client_as("editor")
    page = e.get(f"/admin/posts?school={school_id(db, 'loyola-riverton')}").text
    assert 'name="school"' not in page
    assert "Ignatian News" in page and "Riverton News" not in page


def test_unpublishing_a_draft_changes_nothing(client_as, csrf, db):
    c = client_as("editor")
    create(c, csrf, title="Draft")
    before = post_row(db, "Draft")["updated_at"]
    db.execute("UPDATE posts SET updated_at = '2000-01-01T00:00:00+00:00'")
    db.commit()
    act(c, csrf, post_row(db, "Draft")["id"], "unpublish")
    assert post_row(db, "Draft")["updated_at"] == "2000-01-01T00:00:00+00:00" != before


def test_other_schools_draft_is_not_found_to_delete_and_a_deleted_post_is_gone(client_as, csrf, db):
    create(client_as("editor_b"), csrf, title="Their Draft")
    pid = post_row(db, "Their Draft")["id"]
    assert act(client_as("editor"), csrf, pid, "delete").status_code == 404
    assert count(db) == 1
    owner = client_as("editor_b")
    act(owner, csrf, pid, "delete")
    assert owner.get(f"/admin/posts/{pid}/edit").status_code == 404
