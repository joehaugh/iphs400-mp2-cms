"""The shared Jinja environment (kept apart so routers can import it without cycles)."""
from __future__ import annotations

import posixpath

from fastapi.templating import Jinja2Templates

from app import settings
from app.security import csrf_field

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
templates.env.globals["csrf_field"] = csrf_field


def rel(request, target: str) -> str:
    """`target` (an absolute console path) written relative to the page being served.

    "/admin/posts" seen from /admin/posts/7/edit is "../../posts". The last segment is
    kept as a name so that a link to a folder-like URL never gains a trailing slash.
    """
    start = posixpath.dirname(request.url.path) or "/"
    parent, name = posixpath.split(target)
    return posixpath.normpath(posixpath.join(posixpath.relpath(parent, start), name))


templates.env.globals["rel"] = rel
