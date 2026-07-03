#!/usr/bin/env bash
# Push the local working copy back to S3 at the END of a laptop session.
# Guard: before pushing, it re-checks S3 against the manifest recorded by wiki-pull. If S3 changed
# since your pull (e.g. edits from your phone), it STOPS and lists the changed files rather than
# overwriting them. Re-pull to reconcile, or pass --force to overwrite S3 with your local copy.
#
# Config: set WIKI_BUCKET and WIKI_LOCAL (env vars, or in scripts/wiki-sync.env).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/wiki-sync.env" ] && source "$HERE/wiki-sync.env"
: "${WIKI_BUCKET:?set WIKI_BUCKET (bucket name)}"
: "${WIKI_LOCAL:?set WIKI_LOCAL (local wiki dir)}"
FORCE="${1:-}"

MANIFEST="$WIKI_LOCAL/.wikisync/s3-manifest.txt"
if [ ! -f "$MANIFEST" ]; then
  echo "No manifest at $MANIFEST — run wiki-pull first." >&2
  exit 1
fi

CURRENT="$(mktemp)"
trap 'rm -f "$CURRENT"' EXIT
aws s3api list-objects-v2 --bucket "$WIKI_BUCKET" \
  --query 'Contents[].[Key,ETag]' --output text 2>/dev/null | sort > "$CURRENT"

if ! diff -q "$MANIFEST" "$CURRENT" >/dev/null; then
  if [ "$FORCE" != "--force" ]; then
    echo "CONFLICT: S3 changed since your last pull (edits from another device?)." >&2
    echo "Changed on S3:" >&2
    diff "$MANIFEST" "$CURRENT" | grep -E '^[<>]' | awk '{print "  " $2}' | sort -u >&2
    echo "Re-run wiki-pull to reconcile, or re-run wiki-push --force to overwrite S3 with local." >&2
    exit 1
  fi
  echo "WARNING: --force — overwriting the above S3 changes with your local copy."
fi

EXCLUDES=(--exclude '.wikisync/*' --exclude '.claude/*' --exclude '.git/*' --exclude '.DS_Store')
echo "Pushing $WIKI_LOCAL -> s3://$WIKI_BUCKET ..."
aws s3 sync "$WIKI_LOCAL" "s3://$WIKI_BUCKET" --delete "${EXCLUDES[@]}"

aws s3api list-objects-v2 --bucket "$WIKI_BUCKET" \
  --query 'Contents[].[Key,ETag]' --output text 2>/dev/null | sort > "$MANIFEST"
echo "Done. S3 updated; manifest refreshed."
