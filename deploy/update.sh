#!/usr/bin/env bash
# Run on the server: pull the latest commit and restart the portal.
#
#   bash /opt/services/api-portal/deploy/update.sh
#   SERVICE=my-portal bash deploy/update.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE="${SERVICE:-api-portal}"

cd "$ROOT"
before="$(git rev-parse --short HEAD)"
# config.json and data/ are ignored by git, so pulling never touches them.
git pull --ff-only
after="$(git rev-parse --short HEAD)"
if [ "$before" = "$after" ]; then
  echo "已是最新版本（$after），无需重启"
  exit 0
fi
echo "==> $before -> $after"
git log --oneline "$before..$after"
find "$ROOT/backend" -name __pycache__ -type d -prune -exec rm -rf {} +

systemctl restart "$SERVICE"
sleep 2
if systemctl is-active --quiet "$SERVICE"; then
  echo "$SERVICE 已重启并运行中"
  journalctl -u "$SERVICE" -n 5 --no-pager
else
  echo "$SERVICE 启动失败，最近日志：" >&2
  journalctl -u "$SERVICE" -n 30 --no-pager >&2
  exit 1
fi
