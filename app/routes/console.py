"""Console routes. Every route here requires a signed-in User."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app import dashboard, posts, settings
from app.db import get_db
from app.publish import last_publish, publish
from app.security import current_user, require_admin, verify_csrf
from app.templating import templates

router = APIRouter(prefix="/admin", dependencies=[Depends(current_user)])


@router.get("")
def home(request: Request, user=Depends(current_user),
         db: sqlite3.Connection = Depends(get_db)):
    return templates.TemplateResponse(
        request, "admin/home.html", {
            "title": "Admin", "user": user, "last_publish": last_publish(db),
            "summary": dashboard.summary(db, user)})


@router.get("/content")
def content(request: Request, status: str = "", type: str = "", school: str = "",
            user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    is_admin = user["role"] == "admin"
    chosen = int(school) if is_admin and school.isascii() and school.isdigit() else None
    return templates.TemplateResponse(request, "admin/content.html", {
        "title": "Content", "user": user, "status": status, "kind": type,
        "chosen_school": chosen, "schools": posts.list_schools(db) if is_admin else [],
        "items": dashboard.content_list(db, user, status=status, kind=type, school_id=chosen)})


@router.post("/publish", dependencies=[Depends(verify_csrf)])
def run_publish(user=Depends(require_admin), db: sqlite3.Connection = Depends(get_db)):
    publish(db, settings.SITE)
    return RedirectResponse("/admin", status_code=303)
