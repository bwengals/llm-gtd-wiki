# Change & review workflow

The contract (`template/CLAUDE.md`) uses a **two-tier change policy** plus a **batch review**, so
routine edits don't nag you but nothing slips by unseen. Safety net: S3 versioning (per-file undo).

## Two tiers
- **Auto-apply, never ask, always log** — routine task maintenance: capture to inbox, add a task
  (inferring context/load/time), set a Radar date, mark done, refile, merge duplicates, rebuild the
  dashboard, repair links. Claude just does it and appends one line to `log.md`.
- **Propose-and-confirm** — consequential actions: new external commitments, calendar/email writes,
  deletions, reconciling contradictions, anything ambiguous.

## Batch review
Instead of approving edits one at a time, review them in a batch:
- `log.md` carries a `> Reviewed through: <date>` marker. Every auto-applied change logs a line, so
  entries after the marker are the **pending changeset**.
- Say "review changes" (or run lint). Claude groups the pending entries by file, shows **one
  consolidated changelog** (what changed, where it lives, current wording), and flags judgment calls
  (guessed routing, inferred dates, dedupe merges) with ⚠.
- You reply once with corrections; Claude applies them and appends a fresh marker.

## Undo / rollback
- **One file:** S3 versioning keeps prior versions — restore via the console/CLI.
- **Whole wiki to a given day:** optional daily snapshots (see the repo backlog) make this a one-line
  restore; until then, per-file versions cover most "oops."

## Laptop Claude Code
If you also edit from a local clone, drop `template/settings.json.example` into
`.claude/settings.local.json` — `defaultMode: acceptEdits` stops per-file confirmation prompts, and
the deny rules keep `raw/` immutable and `log.md` append-only. See [laptop-sync.md](laptop-sync.md)
for the pull/push flow (and: pull freely, but confirm before pushing when local and S3 differ).
