#!/usr/bin/env bash
# Pull the wiki from S3 to a local working copy for laptop / Claude Code editing.
# Run this at the START of a laptop session. It makes local an exact mirror of S3 and records a
# manifest of S3's state so wiki-push can later detect changes made elsewhere (e.g. from your phone).
#
# Config: set WIKI_BUCKET and WIKI_LOCAL (env vars, or in scripts/wiki-sync.env).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/wiki-sync.env" ] && source "$HERE/wiki-sync.env"
: "${WIKI_BUCKET:?set WIKI_BUCKET (bucket name)}"
: "${WIKI_LOCAL:?set WIKI_LOCAL (local wiki dir)}"

EXCLUDES=(--exclude '.wikisync/*' --exclude '.claude/*' --exclude '.git/*' --exclude '.DS_Store')

echo "Pulling s3://$WIKI_BUCKET -> $WIKI_LOCAL ..."
aws s3 sync "s3://$WIKI_BUCKET" "$WIKI_LOCAL" --delete "${EXCLUDES[@]}"

mkdir -p "$WIKI_LOCAL/.wikisync"
aws s3api list-objects-v2 --bucket "$WIKI_BUCKET" \
  --query 'Contents[].[Key,ETag]' --output text 2>/dev/null | sort > "$WIKI_LOCAL/.wikisync/s3-manifest.txt"

echo "Done. Local copy mirrors S3; manifest recorded. Edit away, then run wiki-push."
