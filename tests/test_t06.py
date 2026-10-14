"""T06: User management (HTTP seam). Admin only."""
import logging

import pytest

from app import users as store
from app.posts import PostError
from tests.conftest import DEMO_USERS
from tests.test_t02 import create, post_row, school_id

TEMP = "temporary-pw-1"


def user_row(db, email):
    return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def new_user(c, csrf, db, email="new@example.test", role="editor", school="loyola-riverton",
             password=TEMP):
    data = {"email": email, "role": role, "temp_password": password,
            "school_id": str(school_id(db, school)) if school else "",
            "csrf_token": csrf(c, "/admin/users/new")}
    return c.post("/admin/users", data=data, follow_redirects=False)


def edit(c, csrf, uid, role, school_id_value=""):
    return c.post(f"/admin/users/{uid}", follow_redirects=False,
                  data={"role": role, "school_id": school_id_value,
                        "csrf_token": csrf(c, "/admin/users/new")})


def deactivate(c, csrf, uid):
    return c.post(f"/admin/users/{uid}/deactivate", follow_redirects=False,
                  data={"csrf_token": csrf(c, "/admin/users/new")})


def sign_in(c, csrf, email, password):
    return c.post("/login", data={"email": email, "password": password,
                                  "csrf_token": csrf(c)}, follow_redirects=False)


def test_admin_creates_an_editor_who_must_change_the_temporary_password(
        client_as, client, csrf, db):
    assert new_user(client_as("admin"), csrf, db).status_code == 303
    row = user_row(db, "new@example.test")
    assert row["role"] == "editor" and row["school_id"] == school_id(db, "loyola-riverton")
    assert row["must_change_password"] == 1
    assert row["password_hash"].startswith("$argon2") and TEMP not in row["password_hash"]
    assert sign_in(client, csrf, "new@example.test", TEMP).status_code == 303
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/change-password"


def test_admin_creates_an_admin_without_a_school(client_as, csrf, db):
    new_user(client_as("admin"), csrf, db, email="boss@example.test", role="admin", school=None)
    row = user_row(db, "boss@example.test")
    assert row["role"] == "admin" and row["school_id"] is None


def test_create_refuses_bad_input_in_plain_words(client_as, csrf, db):
    a = client_as("admin")
    assert "School" in new_user(a, csrf, db, school=None).text            # editor, no School
    assert "School" in new_user(a, csrf, db, school="network").text       # Network School
    assert "at least" in new_user(a, csrf, db, password="short").text
    assert "already exists" in new_user(a, csrf, db, email=DEMO_USERS["editor"]["email"]).text
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == len(DEMO_USERS)


def test_temporary_password_is_never_shown_or_logged(client_as, csrf, db, caplog):
    caplog.set_level(logging.DEBUG)
    a = client_as("admin")
    refused = new_user(a, csrf, db, school=None)  # re-rendered form
    assert TEMP not in refused.text
    new_user(a, csrf, db)
    assert TEMP not in a.get("/admin/users").text and TEMP not in caplog.text


def test_admin_reassigns_an_editor_and_content_stays_with_its_school(client_as, csrf, db):
    create(client_as("editor"), csrf, title="Stays")
    uid = user_row(db, DEMO_USERS["editor"]["email"])["id"]
    new_school = school_id(db, "xavier-lakeside")
    assert edit(client_as("admin"), csrf, uid, "editor", str(new_school)).status_code == 303
    assert user_row(db, DEMO_USERS["editor"]["email"])["school_id"] == new_school
    assert post_row(db, "Stays")["school_id"] == school_id(db, "st-ignatius")


def test_role_change_takes_effect_at_once(client_as, csrf, db):
    e = client_as("editor")
    assert e.get("/admin/users", follow_redirects=False).status_code == 403
    uid = user_row(db, DEMO_USERS["editor"]["email"])["id"]
    edit(client_as("admin"), csrf, uid, "admin")
    row = user_row(db, DEMO_USERS["editor"]["email"])
    assert row["role"] == "admin" and row["school_id"] is None
    assert e.get("/admin/users").status_code == 200


def test_admin_cannot_demote_or_deactivate_themselves(client_as, csrf, db):
    a = client_as("admin")
    me = user_row(db, DEMO_USERS["admin"]["email"])["id"]
    assert edit(a, csrf, me, "editor", str(school_id(db, "st-ignatius"))).status_code == 400
    assert deactivate(a, csrf, me).status_code == 400
    row = user_row(db, DEMO_USERS["admin"]["email"])
    assert row["role"] == "admin" and row["active"] == 1


def test_deactivation_blocks_sign_in_ends_the_session_and_keeps_content(
        client_as, client, csrf, db):
    e = client_as("editor")
    create(e, csrf, title="Kept", status="published")
    uid = user_row(db, DEMO_USERS["editor"]["email"])["id"]
    assert deactivate(client_as("admin"), csrf, uid).status_code == 303
    assert e.get("/admin", follow_redirects=False).headers["location"] == "/login"
    editor = DEMO_USERS["editor"]
    assert sign_in(client, csrf, editor["email"], editor["password"]).status_code == 401
    assert post_row(db, "Kept") is not None and user_row(db, editor["email"]) is not None
    assert "Deactivated" in client_as("admin").get("/admin/users").text


def test_editor_is_refused_every_user_management_route(client_as, csrf, db):
    e = client_as("editor")
    uid = user_row(db, DEMO_USERS["editor_b"]["email"])["id"]
    token = csrf(e, "/admin")
    for path in ("/admin/users", "/admin/users/new", f"/admin/users/{uid}/edit"):
        assert e.get(path, follow_redirects=False).status_code == 403, path
    for path in ("/admin/users", f"/admin/users/{uid}", f"/admin/users/{uid}/deactivate"):
        r = e.post(path, data={"csrf_token": token, "email": "x@example.test",
                               "role": "admin", "temp_password": TEMP}, follow_redirects=False)
        assert r.status_code == 403, path
    assert user_row(db, DEMO_USERS["editor_b"]["email"])["active"] == 1
    assert user_row(db, "x@example.test") is None
    assert "/admin/users" not in e.get("/admin").text


def test_visitor_is_sent_to_sign_in_and_forms_need_csrf(client, client_as, db):
    assert client.get("/admin/users", follow_redirects=False).status_code == 303
    a = client_as("admin")
    uid = user_row(db, DEMO_USERS["editor"]["email"])["id"]
    assert a.post("/admin/users", data={"email": "n@example.test"}).status_code == 403
    assert a.post(f"/admin/users/{uid}/deactivate").status_code == 403
    assert a.post(f"/admin/users/{uid}", data={"role": "admin"}).status_code == 403
    assert a.get("/admin/users/99999/edit").status_code == 404


def test_the_last_active_admin_cannot_be_demoted_or_deactivated(client_as, csrf, db):
    new_user(client_as("admin"), csrf, db, email="boss@example.test", role="admin", school=None)
    boss = user_row(db, "boss@example.test")
    me = user_row(db, DEMO_USERS["admin"]["email"])
    editor = user_row(db, DEMO_USERS["editor"]["email"])  # any other User acting
    store.deactivate_user(db, editor, me)  # two Admins: one may go
    with pytest.raises(PostError):
        store.deactivate_user(db, editor, boss)
    with pytest.raises(PostError):
        store.update_user(db, editor, boss, role="editor",
                          school_id=str(school_id(db, "st-ignatius")))
    assert user_row(db, "boss@example.test")["active"] == 1


def test_a_non_ascii_digit_in_school_is_a_plain_error_not_a_crash(client_as, csrf, db):
    a = client_as("admin")
    data = {"email": "z@example.test", "role": "editor", "school_id": "²",
            "temp_password": TEMP, "csrf_token": csrf(a, "/admin/users/new")}
    assert a.post("/admin/users", data=data).status_code == 400
