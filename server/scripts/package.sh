#!/usr/bin/env bash
# Build the Lambda deployment zip -> server/dist/lambda.zip (consumed by infra/lambda.tf).
# Usage:  cd server && ./scripts/package.sh
set -euo pipefail

cd "$(dirname "$0")/.."   # server/

DIST="dist"
BUILD="$DIST/build"
ZIP="$DIST/lambda.zip"

rm -rf "$BUILD" "$ZIP"
mkdir -p "$BUILD"

# Install runtime deps for the Lambda platform (manylinux). Adjust --python-version if needed.
pip install \
  --target "$BUILD" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade \
  "mcp>=1.2.0" "starlette>=0.37" "mangum>=0.17" "pyjwt[crypto]>=2.8" "boto3>=1.34"

# App source.
cp -r src/llm_gtd_wiki "$BUILD/llm_gtd_wiki"

( cd "$BUILD" && zip -qr "../lambda.zip" . )
echo "Built $ZIP"
