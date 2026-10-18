#!/usr/bin/env bash
# One-step release: build frontend, package, upload, extract and restart service.
# Local environment configs, cache, and test files are excluded from packaging.
set -euo pipefail

HOST="${HOST:-your.server.ip}"
PORT="${PORT:-22}"
USER_NAME="${USER_NAME:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/services}"
SERVICE="${SERVICE:-api-portal}"

if [ "$HOST" = "your.server.ip" ]; then
  echo "请先在 deploy/deploy.sh 中填写 HOST 和 PORT" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$(basename "$ROOT")"
TARGET="$USER_NAME@$HOST"
TMP="$(mktemp -d)"
PKG="$TMP/api-portal-release.tar.gz"
trap 'rm -rf "$TMP"' EXIT

echo "==> 构建前端"
(cd "$ROOT/frontend" && npm run build --silent)

echo "==> 打包"
TAR_FLAGS=""
if tar --version 2>/dev/null | grep -q bsdtar; then
  TAR_FLAGS="--no-xattrs --no-mac-metadata"
fi

# Exclude local configs, dev data, virtualenvs, and test caches
# shellcheck disable=SC2086
(cd "$(dirname "$ROOT")" && COPYFILE_DISABLE=1 tar $TAR_FLAGS \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='.DS_Store' \
  --exclude='deploy*.sh' \
  --exclude='*.env' \
  --exclude='data*' \
  --exclude='*.sqlite*' \
  --exclude='.pytest_cache' \
  --exclude='.ruff_cache' \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='tests' \
  -czf "$PKG" \
  "$NAME/backend/server.py" \
  "$NAME/backend/runtime" \
  "$NAME/backend/core" \
  "$NAME/backend/api" \
  "$NAME/backend/services" \
  "$NAME/backend/integrations" \
  "$NAME/backend/requirements/base.txt" \
  "$NAME/frontend/dist" \
  "$NAME/deploy" \
  "$NAME/README.md")
echo "    $(du -h "$PKG" | cut -f1)"

echo "==> 上传到 $TARGET:$REMOTE_DIR"
scp -P "$PORT" "$PKG" "$TARGET:$REMOTE_DIR/"

echo "==> 解压并重启"
ssh -p "$PORT" "$TARGET" bash -s -- "$REMOTE_DIR" "$SERVICE" <<'REMOTE'
set -euo pipefail
dir="$1"; service="$2"
cd "$dir"
tar --warning=no-timestamp -xzf api-portal-release.tar.gz 2>/dev/null || tar xzf api-portal-release.tar.gz
rm -f api-portal-release.tar.gz
backend="$dir/api-portal/backend"

if [ ! -d "$backend/.venv" ]; then
  python3 -m venv "$backend/.venv"
fi
"$backend/.venv/bin/python" -m pip install -q --disable-pip-version-check -r "$backend/requirements/base.txt"

find "$backend" -path "$backend/.venv" -prune -o -name __pycache__ -type d -exec rm -rf {} +
systemctl restart "$service"
sleep 2

if systemctl is-active --quiet "$service"; then
  echo "$service 已重启并运行中"
  journalctl -u "$service" -n 5 --no-pager
else
  echo "$service 启动失败，最近日志：" >&2
  journalctl -u "$service" -n 30 --no-pager >&2
  exit 1
fi
REMOTE

echo "==> 完成"
