"""Post routes: list, create, edit, preview. Requires a signed-in User."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import posts as store
from app.db import get_db
from app.markdown import render_markdown
from app.security import current_user, verify_csrf
from app.templating import templates

router = APIRouter(prefix="/admin/posts", dependencies=[Depends(current_user)])


def _form(request, db, user, *, values, post=None, error=None, preview=None, status=200):
    return templates.TemplateResponse(request, "admin/post_form.html", {
        "title": "Edit Post" if post else "New Post", "user": user, "post": post,
        "values": values, "error": error, "preview_html": preview,
        "schools": store.list_schools(db) if user["role"] == "admin" else [],
    }, status_code=status)


def _own_or_404(db, user, post_id: int):
    post = store.get_post(db, user, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")
    return post


@router.get("")
def list_view(request: Request, user=Depends(current_user), db=Depends(get_db)):
    return templates.TemplateResponse(request, "admin/posts.html", {
        "title": "Posts", "user": user, "posts": store.list_posts(db, user)})


@router.get("/new")
def new_view(request: Request, user=Depends(current_user), db=Depends(get_db)):
    return _form(request, db, user, values={"status": "draft"})


@router.post("/preview", dependencies=[Depends(verify_csrf)])
def preview_new(request: Request, user=Depends(current_user), db=Depends(get_db),
                title: str = Form(""), body: str = Form(""), status: str = Form("draft"),
                address: str = Form(""), school_id: str = Form("")):
    values = dict(title=title, body=body, status=status, address=address, school_id=school_id)
    return _form(request, db, user, values=values, preview=render_markdown(body))


@router.post("", dependencies=[Depends(verify_csrf)])
def create(request: Request, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db),
           title: str = Form(""), body: str = Form(""), status: str = Form("draft"),
           address: str = Form(""), school_id: str = Form("")):
    values = dict(title=title, body=body, status=status, address=address, school_id=school_id)
    try:
        target = store.target_school_id(db, user, school_id)
        store.create_post(db, user, school_id=target, title=title, body=body,
                          status=status, address=address)
    except store.PostError as err:
        return _form(request, db, user, values=values, error=str(err), status=400)
    return RedirectResponse("/admin/posts", status_code=303)


@router.get("/{post_id}/edit")
def edit_view(post_id: int, request: Request, user=Depends(current_user), db=Depends(get_db)):
    post = _own_or_404(db, user, post_id)
    return _form(request, db, user, post=post, values=dict(post))


@router.post("/{post_id}/preview", dependencies=[Depends(verify_csrf)])
def preview_existing(post_id: int, request: Request, user=Depends(current_user),
                     db=Depends(get_db), title: str = Form(""), body: str = Form(""),
                     status: str = Form("draft")):
    post = _own_or_404(db, user, post_id)
    values = dict(title=title, body=body, status=status, slug=post["slug"])
    return _form(request, db, user, post=post, values=values, preview=render_markdown(body))


@router.post("/{post_id}", dependencies=[Depends(verify_csrf)])
def update(post_id: int, request: Request, user=Depends(current_user), db=Depends(get_db),
           title: str = Form(""), body: str = Form(""), status: str = Form("draft")):
    post = _own_or_404(db, user, post_id)
    values = dict(title=title, body=body, status=status, slug=post["slug"])
    try:
        store.update_post(db, post, title=title, body=body, status=status)
    except store.PostError as err:
        return _form(request, db, user, post=post, values=values, error=str(err), status=400)
    return RedirectResponse("/admin/posts", status_code=303)
