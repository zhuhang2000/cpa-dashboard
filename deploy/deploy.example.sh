#!/usr/bin/env bash
# One-step release: build the frontend, package what the server needs, upload,
# extract over the previous version and restart. config.json and data/ are not
# in the package, so the server's settings and database are never overwritten.
#
#   cp deploy/deploy.example.sh deploy/deploy.sh   # deploy.sh is git-ignored
#   # fill in HOST / PORT below, then:
#   bash deploy/deploy.sh
#
# Settings can also be overridden per run, e.g. HOST=1.2.3.4 bash deploy/deploy.sh
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
# Keep macOS extended attributes and ._ files out of the archive.
TAR_FLAGS=""
if tar --version 2>/dev/null | grep -q bsdtar; then
  TAR_FLAGS="--no-xattrs --no-mac-metadata"
fi
# shellcheck disable=SC2086
(cd "$(dirname "$ROOT")" && COPYFILE_DISABLE=1 tar $TAR_FLAGS \
  --exclude='__pycache__' --exclude='.DS_Store' --exclude='deploy*.sh' -czf "$PKG" \
  "$NAME/backend/server.py" \
  "$NAME/backend/portal" \
  "$NAME/backend/config.example.json" \
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
tar xzf api-portal-release.tar.gz
rm -f api-portal-release.tar.gz
find "$dir/api-portal/backend" -name __pycache__ -type d -prune -exec rm -rf {} +

if [ ! -f "$dir/api-portal/backend/config.json" ]; then
  echo "首次部署：尚未创建 config.json，请登录服务器按 README 第 3-5 步完成配置、创建管理员并安装 systemd 服务。"
  exit 0
fi
if ! systemctl list-unit-files "$service.service" | grep -q "$service.service"; then
  echo "未找到 $service.service，请按 README 第 5 步安装 systemd 服务。"
  exit 0
fi

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
