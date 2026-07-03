#!/usr/bin/env bash
# Seed an S3 bucket with the starter wiki skeleton (template/wiki/).
# Refuses to overwrite a non-empty bucket unless --force is given.
#
# Usage:  scripts/seed_wiki.sh <bucket-name> [--force]
set -euo pipefail

BUCKET="${1:-}"
FORCE="${2:-}"
if [ -z "$BUCKET" ]; then
  echo "usage: $0 <bucket-name> [--force]" >&2
  exit 1
fi

DIR="$(cd "$(dirname "$0")/../template/wiki" && pwd)"

if [ "$FORCE" != "--force" ]; then
  if aws s3 ls "s3://$BUCKET/" 2>/dev/null | grep -q .; then
    echo "Bucket s3://$BUCKET is not empty — refusing without --force." >&2
    exit 1
  fi
fi

aws s3 sync "$DIR" "s3://$BUCKET/" --exclude '.*'
echo "Seeded s3://$BUCKET from $DIR"
