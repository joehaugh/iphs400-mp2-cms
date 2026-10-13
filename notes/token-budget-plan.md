# Token budget plan

(Part 5.4 of the manual. Written before the first /implement.)

DRAFT: the estimates below are first guesses. Edit them to match what `/model`
offers on my account and what I expect to spend. The report will compare these
against `notes/usage-ledger.csv`.

## Model and effort per stage

| Stage | Model | Effort | Estimate (% of a 5-hour window) |
|---|---|---|---|
| `/research`, quick lookups | Haiku | low | 3% |
| `/grill-with-docs`, `/to-spec`, `/to-tickets` | `opusplan` / Opus | high | 30% |
| `/implement` + `/tdd` (per ticket) | Sonnet | medium | 12% each |
| `/code-review` (per ticket) | Sonnet | high | 5% each |

## Questions from the manual

- **How many 5-hour windows will the 9 tickets take?** About 9 x 17% = 153% of a
  window for the tickets, plus about 33% for research, grill, spec and tickets.
  That is roughly 2 windows, spread over at least 2 days.
- **How much of one week is that?** I have no per-window weekly cost yet. The first
  ledger rows show about 3% of the weekly cap used after 11 turns of setup. After
  T01 I will run `uv run python scripts/usage_report.py --remaining 8` and replace
  this guess with a measured average.
- **What gets cut first if I am wrong?** Extra-credit stretch goals first (they are
  not needed to pass), then `/code-review` effort high -> medium, then I split any
  ticket that pushes a session past 60% context.

## Habits to stretch the window

`/clear` between tickets, Sonnet for implementation, reference files by path
instead of pasting them, and keep `CLAUDE.md` short.
