"""The shared Jinja environment (kept apart so routers can import it without cycles)."""
from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app import settings
from app.security import csrf_field

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
templates.env.globals["csrf_field"] = csrf_field
