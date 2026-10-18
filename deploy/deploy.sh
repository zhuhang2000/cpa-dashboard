#!/usr/bin/env bash
# One-step release: build + package locally, upload, extract on the server, restart.
#
#   bash api-portal/deploy/deploy.sh
#   SKIP_BUILD=1 bash api-portal/deploy/deploy.sh   # reuse the existing frontend/dist
#
# Override the target with env vars, e.g. HOST=1.2.3.4 PORT=22 bash deploy/deploy.sh
set -euo pipefail

HOST="${HOST:-38.75.223.157}"
PORT="${PORT:-7553}"
USER_NAME="${USER_NAME:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/services}"
SERVICE="${SERVICE:-api-portal}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$(dirname "$ROOT")/api-portal-release.tar.gz"
TARGET="$USER_NAME@$HOST"

echo "==> 打包"
bash "$ROOT/deploy/package.sh" >/dev/null
echo "    $PKG ($(du -h "$PKG" | cut -f1))"

echo "==> 上传到 $TARGET:$REMOTE_DIR"
scp -P "$PORT" "$PKG" "$TARGET:$REMOTE_DIR/"

echo "==> 解压并重启"
# config.json and data/ are not in the package, so they are never overwritten.
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
if ! systemctl list-unit-files "$service.service" >/dev/null 2>&1 || \
   ! systemctl list-unit-files "$service.service" | grep -q "$service.service"; then
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
