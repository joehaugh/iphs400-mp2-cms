"""Markdown to sanitized HTML. Every place Markdown is rendered goes through here."""
from __future__ import annotations

import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": True})


def render_markdown(source: str) -> str:
    """Render, then strip scripts, event handlers and unsafe URL schemes."""
    return nh3.clean(_md.render(source))
