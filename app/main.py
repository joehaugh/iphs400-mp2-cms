"""The FastAPI application.

The admin console lives under /admin (sign-in at /login) and the public site
preview at /. Routes live in their own modules under app/routes/ and are
included here. Keep this file small.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

from app import settings
from app.db import init_db
from app.routes import auth, console, pages, posts, users
from app.templating import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="IPHS 400 MP2 CMS", lifespan=lifespan)
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY,
                       same_site="lax", session_cookie="cms_session")
    app.include_router(auth.router)
    app.include_router(console.router)
    app.include_router(posts.router)
    app.include_router(pages.router)
    app.include_router(users.router)

    @app.get("/")
    def public_home(request: Request):
        return templates.TemplateResponse(
            request, "public/home.html",
            {"title": settings.SITE_TITLE, "items": []},
        )

    # Later tickets: add routers to app/routes/ and include them above.
    return app


app = create_app()
