# IPHS 400 — Mini-Project #2 starter (Web CMS)

Click **Use this template** → name your repo **`iphs400-mp2-cms`** → make it **Public**.
Do not fork: a fork arrives without an Issues tab, and your tickets live in Issues.

## Start here

1. `docs/manual_iphs400_mp2-web-cms_20260922.md` — the manual. Read Part 0 and Part 1 first.
2. `docs/mp2-grading-rubric_20260922.md` — how you are graded. Read it **before** you build.
3. `docs/mp2-setup_context-threshold-hook_20260922.md` — Exercise A, in Part 4 of the manual.

## Live URL

https://joehaugh.github.io/iphs400-mp2-cms/

The public site, built by Publish and served from the `gh-pages` branch on GitHub Pages.
The admin console is not on the internet: it runs only on your own computer.

## Run locally

```bash
uv sync
cp .env.example .env                                  # then change the passwords in .env
uv run --env-file .env python scripts/seed_demo.py    # 60 made-up Schools, demo Posts and Pages, 3 users
uv run --env-file .env cms serve                      # the admin console, on your computer only
```

Open http://localhost:8000/login and sign in as `admin@example.test` (or `editor@example.test`)
with the matching password from `.env`. Press **Publish** on the Console page to build `site/`, then
preview it with `python3 -m http.server -d site 8001` and open http://localhost:8001.

The app reads settings from the environment, not from `.env` itself, so run the commands with
`--env-file .env` as shown.

## Content goes live only at the next Publish

Setting a Post or Page to **Published** means "ready", not "live". Nothing reaches
the public site until the Admin presses **Publish** (or runs `uv run cms publish`),
which rebuilds `site/` from scratch for every School at once:

- Only Published content is written. Drafts never leave the database.
- Editing a published item changes the stored copy straight away, but the public
  site shows the old version until the next Publish.
- Setting an item back to draft, or the Admin deleting it, removes it from the public
  site at the next Publish too. Old links to it will then break.
- The console dashboard shows how many items have changed since the last Publish.

The admin console runs only on your own computer. `site/` is generated: never edit it by hand.

## Demo data

```bash
uv run python scripts/seed_demo.py   # 60 made-up Schools, the Network School, an Admin, two Editors
```

Passwords come from `.env` (copy `.env.example`). The Schools are placeholders; the real list comes from the client.

## What is here

```text
.claude/hooks/     the context meter and usage ledger (Exercise A lives in ctx_guard.py)
scripts/           usage_report.py (Exercise B lives in spend()), check_submission.py, seed_demo.py
tests/             the exercise tests, plus helpers such as client_as("editor")
app/, templates/   the T00 skeleton — every CMS feature is yours to build
docs/adr/          two example decision records
```

Two functions are deliberately unfinished and their tests fail until you write them:
`decide()` in `.claude/hooks/ctx_guard.py` and `spend()` in `scripts/usage_report.py`.
Both are graded. Use `/tdd`, as the manual says.

## Deadlines

Stage 1 (`mp2-mvp` tag): Tue Sep 29, 2:40 pm Eastern (soft target).
Stage 2 (`mp2-final` tag): Tue Oct 6, 2:40 pm Eastern, grace until Wed Oct 7, 2:40 pm.

Run `uv run python scripts/check_submission.py --stage 2` before you submit.

## Generative AI Use Statement

*(Required. Replace this section: name the models and skills you used, quote two
prompts you really sent, describe one real model failure, and include a
"Backends used" table if you ever switched providers.)*
