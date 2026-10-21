"""Important notices that admins publish to every user, kept as a dated history."""

from core.db import now_ms
from core.errors import ApiError

MAX_LENGTH = 2000


def _public(row):
    return {
        "id": row["id"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _content(data):
    content = str(data.get("content") or "").strip()
    if not content:
        raise ApiError(400, "通知内容不能为空")
    if len(content) > MAX_LENGTH:
        raise ApiError(400, "通知内容不能超过 %d 字" % MAX_LENGTH)
    return content


def _get(conn, notice_id):
    row = conn.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
    if row is None:
        raise ApiError(404, "通知不存在")
    return {"notice": _public(row)}


def list_notices(conn):
    rows = conn.execute("SELECT * FROM notices ORDER BY created_at DESC, id DESC").fetchall()
    return {"items": [_public(row) for row in rows]}


def latest_at(conn):
    """When the newest notice was published; editing an older one does not make it new again."""
    return conn.execute("SELECT MAX(created_at) FROM notices").fetchone()[0]


def create_notice(conn, operator_id, data):
    content = _content(data)
    now = now_ms()
    notice_id = conn.execute(
        "INSERT INTO notices (content, created_by, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (content, operator_id, now, now),
    ).lastrowid
    return _get(conn, notice_id)


def update_notice(conn, notice_id, data):
    content = _content(data)
    changed = conn.execute(
        "UPDATE notices SET content = ?, updated_at = ? WHERE id = ?",
        (content, now_ms(), notice_id),
    ).rowcount
    if not changed:
        raise ApiError(404, "通知不存在")
    return _get(conn, notice_id)


def delete_notice(conn, notice_id):
    if not conn.execute("DELETE FROM notices WHERE id = ?", (notice_id,)).rowcount:
        raise ApiError(404, "通知不存在")
    return {"ok": True}
