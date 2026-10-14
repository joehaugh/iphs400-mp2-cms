"""Configuration, read from the environment (never hard-code secrets)."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"

# No built-in default: a publicly known key would let anyone forge a session.
# Unset means a random key per process (sessions end when the server restarts).
SECRET_KEY = os.environ.get("CMS_SECRET_KEY") or secrets.token_urlsafe(32)
DATABASE_PATH = Path(os.environ.get("CMS_DATABASE", ROOT / "cms.db"))
SITE_TITLE = os.environ.get("CMS_SITE_TITLE", "My CMS")
# Set this to your Pages URL once you deploy, e.g.
# https://yourname.github.io/iphs400-mp2-cms/
BASE_PATH = os.environ.get("CMS_BASE_PATH", "")
