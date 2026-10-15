# Handoff: submission prep for the Jesuit Schools Network CMS

Written 2026-10-14. Next session focus: finish the non-code deliverables for Mini-Project #2.

## State

All tickets T00–T08 (issues #2–#9) are implemented, reviewed, merged to `main`, and pushed. Each issue has its `/code-review` findings as a comment. Tags `mp2-mvp` (on the T03 commit) and `mp2-final` (on `93f7498`) are pushed. 118 tests pass. See `git log` and the issues for detail; nothing about the code needs redoing.

`uv run python scripts/check_submission.py --stage 2` passes 17 of 22. The five failures are all non-code:

| Failing check | What it needs | Who |
|---|---|---|
| compaction log | `docs/process/compaction-log.md`, written by the `PreCompact` hook (`.claude/hooks/ctx_compact_log.py`). It is graded evidence, so it must come from the hook, never be hand-written. A real `/compact` should create it; if it does not, debug the hook wiring in `.claude/settings.json` (`/hooks`). | agent can debug; the user runs `/compact` |
| handoff | this file, copied into `docs/handoff/` | done |
| report | `docs/iphs400_mp2-web-cms_report_{first}-{last}_{YYYYMMDD}.md`, lowercase | user (content), see the rubric `docs/mp2-grading-rubric_20260922.md` |
| AI Use Statement | the placeholder in `README.md` must be replaced: name models and skills used, quote two real prompts, describe one real model failure, add a "Backends used" table if providers switched | user |
| screenshots | 12 PNGs in `docs/screenshots/`: `{login,dashboard,content-list,editor,users,editor-denied}-{1280,390}.png` | user (needs a browser; run the app with `uv run cms serve` after `scripts/seed_demo.py`) |

## Decisions and gotchas worth knowing

- `check_submission.py` is the instructor's script: do not edit it. Its root-absolute-path check greps every `*.html` in git, including console templates, so console links are made relative through a `rel(request, path)` Jinja helper in `app/templating.py`. Form `action`s are not matched by the check and stay absolute.
- A real failure the e2e tests do not cover: the console requests `style.css`, which 404s under `/admin`, so the console is unstyled. Not a link, so left alone.
- Known, deliberately unfixed gaps (recorded in the review comments on the issues): deleting content is not counted by the dashboard's "changed since last Publish"; draft edits are counted; no reactivate route or temporary-password reset for Users; CSRF no-token tests run as Admin only; `PostError` is reused as the shared error class for Posts, Pages and Users. Suggested follow-up tickets if wanted.
- The database path comes from `CMS_DATABASE` (not `CMS_DATABASE_PATH`). One seed run during T08 used the wrong name and seeded the local `cms.db` instead of a temp file: harmless (git-ignored, idempotent) but easy to repeat.
- Project rules in `CLAUDE.md` apply: write the ticket id to `.claude/state/phase`; post `/code-review` findings on the issue before a ticket-closing commit; commits that close tickets start `T0N:` and end `Closes #N`; add a `Backend:` trailer when `/status` shows a non-Anthropic base URL. Uncommitted `CONTEXT.md` and `notes/usage-ledger.csv` changes pre-date this work and were never part of a ticket commit; ask the user before including them.
- Pushes and tag moves were done only on the user's explicit say-so. Keep doing that.

## Suggested skills

- `research` or the manual (`docs/manual_iphs400_mp2-web-cms_20260922.md`) for what the report must contain.
- `run` to start the app for the screenshots (screenshots themselves need the user's browser, or `anthropic-skills:chrome-browser` if the user wants it automated).
- `diagnosing-bugs` if the `PreCompact` hook still writes nothing after a real `/compact`.
- `writing-for-agents` only if editing `CLAUDE.md` or skills.

## References

- Spec: issue #1. Tickets: issues #2–#9. Glossary: `CONTEXT.md`. Decisions: `docs/adr/`. Rubric: `docs/mp2-grading-rubric_20260922.md`. Manual: `docs/manual_iphs400_mp2-web-cms_20260922.md`.
