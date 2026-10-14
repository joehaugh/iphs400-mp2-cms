"""Console routes. Every route here requires a signed-in User."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.security import current_user
from app.templating import templates

router = APIRouter(prefix="/admin", dependencies=[Depends(current_user)])


@router.get("")
def home(request: Request, user=Depends(current_user)):
    return templates.TemplateResponse(
        request, "admin/home.html", {"title": "Admin", "user": user})
