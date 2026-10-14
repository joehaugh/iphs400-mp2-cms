"""Session-backed CSRF tokens and the signed-in-user dependency."""
from __future__ import annotations

import hmac
import secrets
import sqlite3

from fastapi import Depends, Form, HTTPException, Request
from markupsafe import Markup

from app.db import get_db

CSRF_FIELD = "csrf_token"


def csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_FIELD)
    if not token:
        token = request.session[CSRF_FIELD] = secrets.token_urlsafe(32)
    return token


def csrf_field(request: Request) -> Markup:
    """Hidden input for every state-changing form: {{ csrf_field(request) }}."""
    return Markup('<input type="hidden" name="{}" value="{}">').format(
        CSRF_FIELD, csrf_token(request))


def verify_csrf(request: Request, csrf_token: str = Form("", alias=CSRF_FIELD)) -> None:
    """Dependency for every POST route; rejects a missing or wrong token."""
    expected = request.session.get(CSRF_FIELD, "")
    if not expected or not hmac.compare_digest(expected, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")


def redirect_to(path: str) -> HTTPException:
    return HTTPException(status_code=303, headers={"Location": path})


def _load_user(request: Request, db: sqlite3.Connection) -> sqlite3.Row:
    """The signed-in User, re-read from the database on every request."""
    user_id = request.session.get("user_id")
    user = db.execute(
        "SELECT users.*, schools.name AS school_name FROM users"
        " LEFT JOIN schools ON schools.id = users.school_id"
        " WHERE users.id = ?", (user_id,)).fetchone() if user_id else None
    if (user is None or not user["active"]
            or request.session.get("epoch") != user["session_epoch"]):
        request.session.clear()
        raise redirect_to("/login")
    return user


def end_sessions(db: sqlite3.Connection, user_id: int) -> int:
    """Void every cookie issued so far for this User; returns the new epoch."""
    db.execute("UPDATE users SET session_epoch = session_epoch + 1 WHERE id = ?", (user_id,))
    db.commit()
    return db.execute("SELECT session_epoch FROM users WHERE id = ?", (user_id,)).fetchone()[0]


def current_user_allow_pending(request: Request, db: sqlite3.Connection = Depends(get_db)):
    return _load_user(request, db)


def current_user(request: Request, db: sqlite3.Connection = Depends(get_db)):
    """Console routes depend on this: signed in, active, and past the forced change."""
    user = _load_user(request, db)
    if user["must_change_password"]:
        raise redirect_to("/change-password")
    return user


def require_admin(user=Depends(current_user)):
    """Dependency for Admin-only routes; an Editor gets 403."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only the Admin can do this.")
    return user
