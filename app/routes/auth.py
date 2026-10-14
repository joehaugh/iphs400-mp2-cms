"""Sign in, sign out, and the forced password change."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.db import get_db
from app.passwords import MIN_PASSWORD_LENGTH, hash_password, verify_password
from app.security import current_user_allow_pending, end_sessions, verify_csrf
from app.templating import templates

router = APIRouter()

# One message for every failure, so it never reveals which part was wrong.
BAD_SIGN_IN = "Those sign-in details are not right. Please try again."


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title": "Sign in", "error": None})


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login(request: Request, email: str = Form(""), password: str = Form(""),
          db: sqlite3.Connection = Depends(get_db)):
    user = db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    ok = verify_password(user["password_hash"] if user else None, password)
    if not (ok and user["active"]):
        return templates.TemplateResponse(
            request, "login.html", {"title": "Sign in", "error": BAD_SIGN_IN}, status_code=401)
    request.session.clear()  # fresh session (and CSRF token) on sign-in
    request.session["user_id"] = user["id"]
    request.session["epoch"] = user["session_epoch"]
    return RedirectResponse("/admin", status_code=303)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request, db: sqlite3.Connection = Depends(get_db)):
    # Cookies are stateless, so clearing ours is not enough: void any copy too.
    if request.session.get("user_id"):
        end_sessions(db, request.session["user_id"])
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/change-password")
def change_password_form(request: Request, user=Depends(current_user_allow_pending)):
    return templates.TemplateResponse(
        request, "change_password.html", {"title": "Choose a new password", "user": user,
                                          "error": None, "min_length": MIN_PASSWORD_LENGTH})


@router.post("/change-password", dependencies=[Depends(verify_csrf)])
def change_password(request: Request, current_password: str = Form(""),
                    new_password: str = Form(""), confirm_password: str = Form(""),
                    user=Depends(current_user_allow_pending),
                    db: sqlite3.Connection = Depends(get_db)):
    error = None
    if not verify_password(user["password_hash"], current_password):
        error = "Your current password is not right."
    elif new_password != confirm_password:
        error = "The two new passwords do not match."
    elif len(new_password) < MIN_PASSWORD_LENGTH:
        error = f"Choose a password of at least {MIN_PASSWORD_LENGTH} characters."
    elif new_password == current_password:
        error = "Choose a password different from the temporary one."
    if error:
        return templates.TemplateResponse(
            request, "change_password.html",
            {"title": "Choose a new password", "user": user, "error": error,
             "min_length": MIN_PASSWORD_LENGTH}, status_code=400)
    db.execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
               (hash_password(new_password), user["id"]))
    db.commit()
    request.session["epoch"] = end_sessions(db, user["id"])  # other cookies die, this one lives
    return RedirectResponse("/admin", status_code=303)
