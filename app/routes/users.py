"""User management routes. Admin only: an Editor is refused on every one."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import users as store
from app.db import get_db
from app.posts import PostError
from app.security import require_admin, verify_csrf
from app.templating import templates

router = APIRouter(prefix="/admin/users", dependencies=[Depends(require_admin)])


def _form(request, db, user, *, values, target=None, error=None, status=200):
    return templates.TemplateResponse(request, "admin/user_form.html", {
        "title": "Edit User" if target else "New User", "user": user, "target": target,
        "values": values, "error": error, "schools": store.list_member_schools(db),
        "min_length": store.MIN_PASSWORD_LENGTH}, status_code=status)


def _target_or_404(db, user_id: int):
    target = store.get_user(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return target


@router.get("")
def list_view(request: Request, user=Depends(require_admin), db=Depends(get_db),
              error: str = ""):
    return templates.TemplateResponse(request, "admin/users.html", {
        "title": "Users", "user": user, "users": store.list_users(db), "error": error})


@router.get("/new")
def new_view(request: Request, user=Depends(require_admin), db=Depends(get_db)):
    return _form(request, db, user, values={"role": "editor"})


@router.post("", dependencies=[Depends(verify_csrf)])
def create(request: Request, user=Depends(require_admin), db: sqlite3.Connection = Depends(get_db),
           email: str = Form(""), role: str = Form("editor"), school_id: str = Form(""),
           temp_password: str = Form("")):
    values = dict(email=email, role=role, school_id=school_id)  # never echo the password
    try:
        store.create_user(db, email=email, role=role, school_id=school_id,
                          temp_password=temp_password)
    except PostError as err:
        return _form(request, db, user, values=values, error=str(err), status=400)
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/{user_id}/edit")
def edit_view(user_id: int, request: Request, user=Depends(require_admin), db=Depends(get_db)):
    target = _target_or_404(db, user_id)
    values = {"email": target["email"], "role": target["role"],
              "school_id": "" if target["school_id"] is None else str(target["school_id"])}
    return _form(request, db, user, target=target, values=values)


@router.post("/{user_id}", dependencies=[Depends(verify_csrf)])
def update(user_id: int, request: Request, user=Depends(require_admin), db=Depends(get_db),
           role: str = Form(""), school_id: str = Form("")):
    target = _target_or_404(db, user_id)
    values = dict(email=target["email"], role=role, school_id=school_id)
    try:
        store.update_user(db, user, target, role=role, school_id=school_id)
    except PostError as err:
        return _form(request, db, user, target=target, values=values, error=str(err), status=400)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/{user_id}/deactivate", dependencies=[Depends(verify_csrf)])
def deactivate(request: Request, user_id: int, user=Depends(require_admin), db=Depends(get_db)):
    target = _target_or_404(db, user_id)
    try:
        store.deactivate_user(db, user, target)
    except PostError as err:
        return templates.TemplateResponse(request, "admin/users.html", {
            "title": "Users", "user": user, "users": store.list_users(db), "error": str(err)},
            status_code=400)
    return RedirectResponse("/admin/users", status_code=303)
