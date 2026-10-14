"""T01: sign in, sign out, forced password change, CSRF, and the seed."""
import logging

from tests.conftest import DEMO_USERS


def sign_in(client, csrf, who="editor", password=None, follow=False):
    user = DEMO_USERS[who]
    return client.post(
        "/login",
        data={"email": user["email"], "password": password or user["password"],
              "csrf_token": csrf(client)},
        follow_redirects=follow)


def test_console_redirects_visitor_to_sign_in(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_correct_credentials_sign_in(client, csrf):
    response = sign_in(client, csrf)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    assert client.get("/admin").status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_plain_message(client, csrf):
    wrong_pw = sign_in(client, csrf, password="nope")
    unknown = client.post("/login", data={"email": "nobody@example.test",
                                          "password": "nope",
                                          "csrf_token": csrf(client)})
    assert wrong_pw.status_code == unknown.status_code == 401
    message = "Those sign-in details are not right"
    assert message in wrong_pw.text and message in unknown.text
    assert client.get("/admin", follow_redirects=False).status_code == 303
    lowered = wrong_pw.text.lower()
    assert "wrong password" not in lowered and "no such" not in lowered


def test_deactivated_user_cannot_sign_in(client, csrf, db):
    db.execute("UPDATE users SET active = 0 WHERE email = ?", (DEMO_USERS["editor"]["email"],))
    db.commit()
    assert sign_in(client, csrf).status_code == 401


def test_passwords_are_stored_only_as_argon2_hashes(db):
    for user in DEMO_USERS.values():
        stored = db.execute("SELECT password_hash FROM users WHERE email = ?",
                            (user["email"],)).fetchone()[0]
        assert stored.startswith("$argon2")
        assert user["password"] not in stored


def test_passwords_are_never_logged(client, csrf, caplog):
    caplog.set_level(logging.DEBUG)
    sign_in(client, csrf, password="a-wrong-secret-pw")
    sign_in(client, csrf)
    for secret in ("a-wrong-secret-pw", DEMO_USERS["editor"]["password"]):
        assert secret not in caplog.text


def test_sign_out_ends_the_session(client_as, csrf):
    c = client_as("editor")
    response = c.post("/logout", data={"csrf_token": csrf(c, "/admin")},
                      follow_redirects=False)
    assert response.status_code == 303
    assert c.get("/admin", follow_redirects=False).status_code == 303


def test_deactivation_ends_an_existing_session_at_once(client_as, db):
    c = client_as("editor")
    assert c.get("/admin").status_code == 200
    db.execute("UPDATE users SET active = 0 WHERE email = ?", (DEMO_USERS["editor"]["email"],))
    db.commit()
    response = c.get("/admin", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/login"


# --- forced password change -------------------------------------------------

def flag_must_change(db, who="editor"):
    db.execute("UPDATE users SET must_change_password = 1 WHERE email = ?",
               (DEMO_USERS[who]["email"],))
    db.commit()


def test_flagged_user_is_redirected_until_they_choose_a_password(client_as, csrf, db):
    flag_must_change(db)
    c = client_as("editor")
    response = c.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/change-password"

    token = csrf(c, "/change-password")
    old = DEMO_USERS["editor"]["password"]
    done = c.post("/change-password",
                  data={"current_password": old, "new_password": "my-own-new-password",
                        "confirm_password": "my-own-new-password", "csrf_token": token},
                  follow_redirects=False)
    assert done.status_code == 303 and done.headers["location"] == "/admin"
    assert c.get("/admin").status_code == 200


def test_new_password_replaces_the_old_one(client, csrf, client_as, db):
    flag_must_change(db)
    c = client_as("editor")
    c.post("/change-password",
           data={"current_password": DEMO_USERS["editor"]["password"],
                 "new_password": "my-own-new-password",
                 "confirm_password": "my-own-new-password",
                 "csrf_token": csrf(c, "/change-password")})
    assert sign_in(client, csrf).status_code == 401  # old password
    assert sign_in(client, csrf, password="my-own-new-password").status_code == 303


def test_change_password_rejects_bad_choices(client_as, csrf, db):
    flag_must_change(db)
    c = client_as("editor")
    old = DEMO_USERS["editor"]["password"]
    for current, new, confirm in [
        (old, "short", "short"),
        (old, "long-enough-pw", "different-pw-here"),
        (old, old, old),
        ("not-my-password", "long-enough-pw", "long-enough-pw"),
    ]:
        response = c.post("/change-password",
                          data={"current_password": current, "new_password": new,
                                "confirm_password": confirm,
                                "csrf_token": csrf(c, "/change-password")})
        assert response.status_code == 400
    assert c.get("/admin", follow_redirects=False).status_code == 303  # still flagged


# --- CSRF --------------------------------------------------------------------

def test_posts_without_a_csrf_token_are_rejected(client_as, client, db):
    user = DEMO_USERS["editor"]
    no_token = client.post("/login", data={"email": user["email"],
                                           "password": user["password"]})
    assert no_token.status_code == 403
    assert client.get("/admin", follow_redirects=False).status_code == 303

    c = client_as("editor")
    assert c.post("/logout", data={}).status_code == 403
    assert c.get("/admin").status_code == 200  # the rejected logout changed nothing
    bad = c.post("/logout", data={"csrf_token": "forged"})
    assert bad.status_code == 403

    flag_must_change(db)
    assert c.post("/change-password",
                  data={"current_password": user["password"],
                        "new_password": "my-own-new-password",
                        "confirm_password": "my-own-new-password"}).status_code == 403


def test_every_form_carries_a_csrf_token(client, client_as, db):
    assert 'name="csrf_token"' in client.get("/login").text
    assert 'name="csrf_token"' in client_as("editor").get("/admin").text


# --- seed and console home ---------------------------------------------------

def test_seed_has_schools_network_school_admin_and_editors_for_two_schools(db):
    assert db.execute("SELECT COUNT(*) FROM schools WHERE is_network = 1").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM schools WHERE is_network = 0").fetchone()[0] >= 3
    rows = db.execute("SELECT role, school_id FROM users").fetchall()
    assert sum(r["role"] == "admin" for r in rows) == 1
    editor_schools = {r["school_id"] for r in rows if r["role"] == "editor"}
    assert len(editor_schools) == 2 and None not in editor_schools


def test_client_as_signs_in_as_each_seeded_user(client_as):
    for who in DEMO_USERS:
        assert client_as(who).get("/admin").status_code == 200


def test_console_home_shows_role_and_school(client_as, db):
    schools = {r["email"]: r["name"] for r in db.execute(
        "SELECT email, schools.name FROM users JOIN schools ON schools.id = users.school_id")}
    for who in ("editor", "editor_b"):
        page = client_as(who).get("/admin").text
        assert "Editor" in page
        assert schools[DEMO_USERS[who]["email"]] in page
    other = schools[DEMO_USERS["editor_b"]["email"]]
    assert other not in client_as("editor").get("/admin").text

    admin_page = client_as("admin").get("/admin").text
    assert "Admin" in admin_page and "Network" in admin_page


def test_seeding_twice_changes_nothing(db):
    from app.seed import seed
    before = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    seed(db, {key: u["password"] for key, u in DEMO_USERS.items()})
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == before


def test_a_copied_session_cookie_dies_at_sign_out(client_as, csrf):
    from fastapi.testclient import TestClient
    from app.main import create_app

    c = client_as("editor")
    stolen = c.cookies.get("cms_session")
    c.post("/logout", data={"csrf_token": csrf(c, "/admin")})
    replay = TestClient(create_app())
    replay.cookies.set("cms_session", stolen)
    assert replay.get("/admin", follow_redirects=False).status_code == 303


def test_changing_password_voids_other_sessions_but_not_this_one(client_as, csrf, db):
    flag_must_change(db)
    c = client_as("editor")
    other = client_as("editor")
    c.post("/change-password",
           data={"current_password": DEMO_USERS["editor"]["password"],
                 "new_password": "my-own-new-password",
                 "confirm_password": "my-own-new-password",
                 "csrf_token": csrf(c, "/change-password")})
    assert c.get("/admin").status_code == 200
    assert other.get("/admin", follow_redirects=False).status_code == 303
