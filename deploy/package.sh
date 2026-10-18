#!/usr/bin/env bash
# Packs only the files the server needs into api-portal-release.tar.gz
# (written next to the api-portal folder).
#
#   bash deploy/package.sh              # rebuilds frontend/dist first when node_modules exists
#   SKIP_BUILD=1 bash deploy/package.sh # package the existing frontend/dist as-is
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$(basename "$ROOT")"
OUT="$(dirname "$ROOT")/api-portal-release.tar.gz"

if [ "${SKIP_BUILD:-0}" != "1" ] && command -v npm >/dev/null 2>&1 && [ -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm run build)
fi
if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  echo "frontend/dist is missing: run 'npm install && npm run build' in frontend/ first" >&2
  exit 1
fi

# Keep macOS extended attributes and ._ files out of the archive.
TAR_FLAGS=""
if tar --version 2>/dev/null | grep -q bsdtar; then
  TAR_FLAGS="--no-xattrs --no-mac-metadata"
fi

cd "$(dirname "$ROOT")"
# shellcheck disable=SC2086
COPYFILE_DISABLE=1 tar $TAR_FLAGS --exclude='__pycache__' --exclude='.DS_Store' -czf "$OUT" \
  "$NAME/backend/server.py" \
  "$NAME/backend/portal" \
  "$NAME/backend/config.example.json" \
  "$NAME/frontend/dist" \
  "$NAME/deploy" \
  "$NAME/README.md"

echo "created $OUT ($(du -h "$OUT" | cut -f1))"
tar -tzf "$OUT"
