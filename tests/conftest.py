"""Shared test fixtures.

`client` gives you the app. `client_as(role)` gives you a client that is logged
in as a seeded user of that role — it works as soon as your login route exists,
so access-control tests stay one line:

    def test_editor_cannot_manage_users(client_as):
        assert client_as("editor").get("/admin/users").status_code in (302, 403)
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import settings
from app.db import connect, init_db
from app.main import create_app
from app.seed import seed

# Matches app/seed.py. Passwords come from the environment in
# scripts/seed_demo.py; in tests they are fixed and meaningless.
# "editor" and "editor_b" belong to different Schools, for cross-School tests.
DEMO_USERS = {
    "admin": {"email": "admin@example.test", "password": "test-admin-pw"},
    "editor": {"email": "editor@example.test", "password": "test-editor-pw"},
    "editor_b": {"email": "editor-b@example.test", "password": "test-editor-b-pw"},
}

_CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture(autouse=True)
def cheap_hashing(monkeypatch):
    """Same argon2 algorithm, minimal cost, so seeding users per test stays fast."""
    from argon2 import PasswordHasher
    from app import passwords

    hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    monkeypatch.setattr(passwords, "_hasher", hasher)
    monkeypatch.setattr(passwords, "_DUMMY_HASH", hasher.hash("not-a-real-password"))


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    """A fresh seeded database for every test; returns an open connection."""
    monkeypatch.setattr(settings, "DATABASE_PATH", tmp_path / "test.db")
    conn = connect()
    init_db(conn)
    seed(conn, {key: u["password"] for key, u in DEMO_USERS.items()})
    yield conn
    conn.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def csrf():
    """csrf(client, path) -> the CSRF token from the form served at `path`."""

    def _token(c: TestClient, path: str = "/login") -> str:
        match = _CSRF.search(c.get(path).text)
        assert match, f"No CSRF token in the form at {path}"
        return match.group(1)

    return _token


@pytest.fixture
def client_as(csrf):
    """Return a factory: client_as("editor") -> a logged-in TestClient."""

    def _login(role: str) -> TestClient:
        user = DEMO_USERS[role]
        c = TestClient(create_app())
        response = c.post("/login", data={"email": user["email"],
                                          "password": user["password"],
                                          "csrf_token": csrf(c)},
                          follow_redirects=False)
        assert response.status_code in (200, 302, 303), (
            f"Login as {role} failed with {response.status_code}")
        return c

    return _login
