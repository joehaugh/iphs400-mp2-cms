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

**Models.** Claude Sonnet 5.5 (`claude-sonnet-5-5`) on medium effort, through Claude Code, for every session: the grill, the spec, the tickets, all eight tickets and the review of each. The report is my own writing, except the two tables and two factual lines that Claude added from the usage ledger and the session record. Claude also assembled this statement from my report and my messages.

**Skills.** `/setup-matt-pocock-skills`, `/ask-matt`, `/research`, `/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement` (every ticket from #2) and `/code-review`. `/grill-with-docs` is where the scope was decided. For example, I told Claude the Editor should only edit their own School and see only their own updated Posts.

**Two prompts I really sent.**

1. When I was choosing the project, I asked: “Is it too complicated to make a mock networking website for the jesuit secondary schools in the US. There are 60 schools according to wikipedia. Do you want more details yet or should we just begin going through the instructions?” It was a taller task than I expected, so it became a news site with a public page for each School instead of a full networking site.
2. When Claude suggested a narrower framing (Jennifer as Admin, School Editors limited to their School, a public site of published Posts and Pages), I replied: “I do like this and it seems feesible. However at the end if the website works well, could we show a mockup for what the site would be with more of a social network feel?” I accepted the framing and kept the social-network idea for later, which is why the report ends with the interactive map of the Schools.

**One real model failure.** Claude seeded the real `cms.db` with throwaway test passwords by using the wrong environment variable name, so my own `.env` passwords were rejected at login. The stored hashes matched the throwaway passwords, so the database was fine but held the wrong ones. The server also had not been running. We worked around it by signing in with the throwaway passwords. The proper fix, deleting `cms.db` and reseeding with `uv run --env-file .env`, is still not done. A smaller failure: Claude told me it had checked that the published pages did not contain a real name from my notes when it had not run the check. It corrected itself within seconds and the later check found nothing.

**Backends used.**

| Provider | Model | Used for | Backup provider |
|---|---|---|---|
| Anthropic | Sonnet 5.5 (`claude-sonnet-5-5`) | All sessions | None |

The full report is in `docs/`, and the session transcripts are in `docs/transcripts/`.
