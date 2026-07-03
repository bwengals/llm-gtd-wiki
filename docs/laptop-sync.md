# Laptop ↔ S3 sync (pull → work → push)

**S3 is the single source of truth.** Day-to-day capture/clarify/review happens through the Claude
app connector (phone/desktop). But some work is better on a laptop with **Claude Code** — structural
or bulk changes, refactors, or anything that runs scripts. For that, use a **local clone bracketed by
sync**: pull at the start, push at the end.

## The model
```
wiki-pull   →   edit locally with Claude Code / run scripts   →   wiki-push
(S3 → local,                                                     (local → S3,
 record manifest)                                                guarded by manifest)
```
- The local copy is authoritative **only during a bracketed session**. Between sessions it's a
  potentially-stale snapshot — don't trust it as truth, and don't edit on your phone mid-session.

## The scripts (`scripts/`)
Config via `scripts/wiki-sync.env` (gitignored; copy from `wiki-sync.env.example`):
```
export WIKI_BUCKET="your-gtd-wiki-bucket"
export WIKI_LOCAL="$HOME/path/to/local/wiki"
```

- **`wiki-pull.sh`** — `aws s3 sync s3://$WIKI_BUCKET → $WIKI_LOCAL --delete`, then records a manifest
  (`$WIKI_LOCAL/.wikisync/s3-manifest.txt` = every S3 key + ETag). Run at the **start** of a session.
- **`wiki-push.sh`** — re-lists S3 and diffs it against the manifest:
  - **No change since pull** → `aws s3 sync local → S3 --delete`, then refreshes the manifest.
  - **S3 changed since pull** (e.g. a phone edit) → **stops** and lists the changed keys. Reconcile by
    re-running `wiki-pull` (pull the other-device changes down, redo your edit), or override with
    `wiki-push.sh --force` to overwrite S3 with local.

Excluded from both directions: `.wikisync/`, `.claude/`, `.git/`, `.DS_Store`.

## Why this design
- Matches how the laptop is actually used: **occasional, deliberate, bracketed** sessions — not
  continuous editing. So pull-at-start/push-at-end is natural, and the destructive `--delete` is safe
  because of the manifest guard.
- **No new dependencies** — just the AWS CLI. Scripts run on real local files, so anything (Python
  scripts, bulk edits) works normally.
- The guard's whole job is the one real risk: a phone edit landing while you have a stale local copy.
  It never silently clobbers — worst case it makes you re-pull.

## Caveats
- **Run `wiki-pull` only at the start** (it `--delete`s local files not on S3 — don't run it on top of
  un-pushed local work).
- Concurrency is still last-write-wins at the object level; the manifest guard operates at
  session granularity, not per-keystroke.
- Conflict detection uses S3 ETags (content hashes for these small single-part objects), so a real
  content change on S3 is always detected; an identical rewrite is correctly ignored.

## Alternatives considered (and why not)
- **rclone bisync** — true continuous two-way sync with conflict handling; more machinery + another
  binary than occasional laptop work needs. Reach for it only if you want sloppy two-way editing.
- **FUSE mount (s3fs / mountpoint-s3)** — one live copy, no sync step, but macOS FUSE (macFUSE kernel
  extension) is finicky and permission-heavy. Not worth it here.
