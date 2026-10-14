"""Page routes: list, create, edit, preview, unpublish, delete. Requires a signed-in User."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import pages as store
from app.db import get_db
from app.markdown import render_markdown
from app.security import current_user, verify_csrf
from app.templating import templates

router = APIRouter(prefix="/admin/pages", dependencies=[Depends(current_user)])


def _form(request, db, user, *, values, page=None, error=None, preview=None, status=200):
    # Pin order applies to Network School Pages, written only by the Admin.
    pinnable = user["role"] == "admin" and (bool(page["is_network"]) if page else True)
    return templates.TemplateResponse(request, "admin/page_form.html", {
        "title": "Edit Page" if page else "New Page", "user": user, "page": page,
        "values": values, "error": error, "preview_html": preview, "pinnable": pinnable,
        "schools": store.list_schools(db) if user["role"] == "admin" else [],
        "can_delete": bool(page) and store.can_delete(user, page),
    }, status_code=status)


def _own_or_404(db, user, page_id: int):
    page = store.get_page(db, user, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return page


@router.get("")
def list_view(request: Request, school: str = "", user=Depends(current_user),
              db=Depends(get_db)):
    chosen = int(school) if school.isdigit() else None
    return templates.TemplateResponse(request, "admin/pages.html", {
        "title": "Pages", "user": user, "pages": store.list_pages(db, user, chosen),
        "schools": store.list_schools(db) if user["role"] == "admin" else [],
        "chosen_school": chosen if user["role"] == "admin" else None})


@router.get("/new")
def new_view(request: Request, user=Depends(current_user), db=Depends(get_db)):
    return _form(request, db, user, values={"status": "draft"})


@router.post("/preview", dependencies=[Depends(verify_csrf)])
def preview_new(request: Request, user=Depends(current_user), db=Depends(get_db),
                title: str = Form(""), body: str = Form(""), status: str = Form("draft"),
                address: str = Form(""), school_id: str = Form(""), pin_order: str = Form("")):
    values = dict(title=title, body=body, status=status, address=address,
                  school_id=school_id, pin_order=pin_order)
    return _form(request, db, user, values=values, preview=render_markdown(body))


@router.post("", dependencies=[Depends(verify_csrf)])
def create(request: Request, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db),
           title: str = Form(""), body: str = Form(""), status: str = Form("draft"),
           address: str = Form(""), school_id: str = Form(""), pin_order: str = Form("")):
    values = dict(title=title, body=body, status=status, address=address,
                  school_id=school_id, pin_order=pin_order)
    try:
        target = store.target_school_id(db, user, school_id, "Page")
        store.create_page(db, user, school_id=target, title=title, body=body,
                          status=status, address=address, pin_order=pin_order)
    except store.PostError as err:
        return _form(request, db, user, values=values, error=str(err), status=400)
    return RedirectResponse("/admin/pages", status_code=303)


@router.get("/{page_id}/edit")
def edit_view(page_id: int, request: Request, user=Depends(current_user), db=Depends(get_db)):
    page = _own_or_404(db, user, page_id)
    values = {**dict(page), "pin_order": "" if page["pin_order"] is None else page["pin_order"]}
    return _form(request, db, user, page=page, values=values)


@router.post("/{page_id}/preview", dependencies=[Depends(verify_csrf)])
def preview_existing(page_id: int, request: Request, user=Depends(current_user),
                     db=Depends(get_db), title: str = Form(""), body: str = Form(""),
                     status: str = Form("draft"), pin_order: str = Form("")):
    page = _own_or_404(db, user, page_id)
    values = dict(title=title, body=body, status=status, slug=page["slug"], pin_order=pin_order)
    return _form(request, db, user, page=page, values=values, preview=render_markdown(body))


@router.post("/{page_id}", dependencies=[Depends(verify_csrf)])
def update(page_id: int, request: Request, user=Depends(current_user), db=Depends(get_db),
           title: str = Form(""), body: str = Form(""), status: str = Form("draft"),
           pin_order: str = Form("")):
    page = _own_or_404(db, user, page_id)
    values = dict(title=title, body=body, status=status, slug=page["slug"], pin_order=pin_order)
    if user["role"] != "admin":
        pin_order = ""  # only the Admin pins
    try:
        store.update_page(db, page, title=title, body=body, status=status, pin_order=pin_order)
    except store.PostError as err:
        return _form(request, db, user, page=page, values=values, error=str(err), status=400)
    return RedirectResponse("/admin/pages", status_code=303)


@router.post("/{page_id}/unpublish", dependencies=[Depends(verify_csrf)])
def unpublish(page_id: int, user=Depends(current_user), db=Depends(get_db)):
    store.set_draft(db, _own_or_404(db, user, page_id))
    return RedirectResponse("/admin/pages", status_code=303)


@router.post("/{page_id}/delete", dependencies=[Depends(verify_csrf)])
def delete(page_id: int, user=Depends(current_user), db=Depends(get_db)):
    page = _own_or_404(db, user, page_id)
    if not store.can_delete(user, page):
        raise HTTPException(status_code=403,
                            detail="Only the Admin can delete a published Page. "
                                   "Set it back to draft instead.")
    store.delete_page(db, page)
    return RedirectResponse("/admin/pages", status_code=303)
