"""User management data access. Admin only; the routes enforce that.

A deactivated User keeps their row, so the Posts and Pages they wrote stay with
their School. Passwords are hashed here and never returned or logged.
"""
from __future__ import annotations

import sqlite3

from app.passwords import MIN_PASSWORD_LENGTH, hash_password
from app.posts import PostError
from app.security import end_sessions

ROLES = ("admin", "editor")


def list_users(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
        "SELECT users.id, users.email, users.role, users.active, schools.name AS school_name"
        " FROM users LEFT JOIN schools ON schools.id = users.school_id"
        " ORDER BY users.active DESC, users.email").fetchall()


def get_user(db: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_member_schools(db: sqlite3.Connection) -> list[sqlite3.Row]:
    """The Network School is written by the Admin alone, so no Editor is assigned to it."""
    return db.execute("SELECT id, name FROM schools WHERE is_network = 0 ORDER BY name").fetchall()


def _role_and_school(db, role: str, school_id: str) -> tuple[str, int | None]:
    if role not in ROLES:
        raise PostError("Role must be Admin or Editor.")
    if role == "admin":
        return role, None
    if school_id.isascii() and school_id.isdigit() and db.execute(
            "SELECT 1 FROM schools WHERE id = ? AND is_network = 0",
            (int(school_id),)).fetchone():
        return role, int(school_id)
    raise PostError("Choose the School this Editor writes for.")


def create_user(db, *, email: str, role: str, school_id: str, temp_password: str) -> int:
    email = email.strip().lower()
    if "@" not in email:
        raise PostError("Enter the User's email address.")
    role, school = _role_and_school(db, role, school_id)
    if len(temp_password) < MIN_PASSWORD_LENGTH:
        raise PostError(f"The temporary password needs at least {MIN_PASSWORD_LENGTH} characters.")
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise PostError("A User with that email already exists.")
    cur = db.execute(
        "INSERT INTO users (email, password_hash, role, school_id, must_change_password)"
        " VALUES (?, ?, ?, ?, 1)", (email, hash_password(temp_password), role, school))
    db.commit()
    return cur.lastrowid


def _keep_one_admin(db, leaving: sqlite3.Row) -> None:
    """Refuse a change that would leave the console with no active Admin."""
    others = db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1"
                        " AND id != ?", (leaving["id"],)).fetchone()[0]
    if not others:
        raise PostError("The console needs at least one active Admin.")


def update_user(db, actor, target: sqlite3.Row, *, role: str, school_id: str) -> None:
    """Change role and School. Content is untouched: it belongs to its School, not the User."""
    role, school = _role_and_school(db, role, school_id)
    if target["id"] == actor["id"] and role != target["role"]:
        raise PostError("You cannot change your own role; ask another Admin.")
    if target["role"] == "admin" and role != "admin":
        _keep_one_admin(db, target)
    db.execute("UPDATE users SET role = ?, school_id = ? WHERE id = ?",
               (role, school, target["id"]))
    db.commit()


def deactivate_user(db, actor, target: sqlite3.Row) -> None:
    if target["id"] == actor["id"]:
        raise PostError("You cannot deactivate your own account.")
    if target["role"] == "admin":
        _keep_one_admin(db, target)
    db.execute("UPDATE users SET active = 0 WHERE id = ?", (target["id"],))
    db.commit()
    end_sessions(db, target["id"])
