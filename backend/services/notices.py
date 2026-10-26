"""Important notices that admins publish to every user, kept as a dated history."""

from core.db import now_ms

# ---- Shared ----


def _public(row):
    return {
        "id": row["id"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---- User operations ----


def list_notices(conn):
    rows = conn.execute("SELECT * FROM notices ORDER BY created_at DESC, id DESC").fetchall()
    return {"items": [_public(row) for row in rows]}


def latest_at(conn):
    """When the newest notice was published; editing an older one does not make it new again."""
    return conn.execute("SELECT MAX(created_at) FROM notices").fetchone()[0]


# ---- Administrator operations ----


def _get(conn, notice_id):
    row = conn.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
    return {"notice": _public(row)}


def create_notice(conn, operator_id, data):
    now = now_ms()
    notice_id = conn.execute(
        "INSERT INTO notices (content, created_by, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (data["content"], operator_id, now, now),
    ).lastrowid
    return _get(conn, notice_id)


def update_notice(conn, notice_id, data):
    conn.execute(
        "UPDATE notices SET content = ?, updated_at = ? WHERE id = ?",
        (data["content"], now_ms(), notice_id),
    )
    return _get(conn, notice_id)


def delete_notice(conn, notice_id):
    conn.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
    return {"ok": True}
