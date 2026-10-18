"""Exercise the actual entry point from outside backend/ with isolated config."""

import shutil
import subprocess
import sys
from pathlib import Path

from core.db import MIGRATIONS, connect
from core.security import verify_password

BACKEND = Path(__file__).resolve().parents[1]


def test_cli_commands_keep_paths_and_database_format(tmp_path):
    backend = tmp_path / "backend"
    backend.mkdir()
    shutil.copy2(BACKEND / "server.py", backend / "server.py")
    for folder in ("runtime", "core", "api", "services", "integrations"):
        shutil.copytree(
            BACKEND / folder, backend / folder, ignore=shutil.ignore_patterns("__pycache__", ".env")
        )
    config = backend / "core" / ".env"

    def run(*args):
        result = subprocess.run(
            [sys.executable, str(backend / "server.py"), *args],
            cwd=tmp_path,
            text=True,
            capture_output=True,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    help_text = run("--help")
    assert "create-admin" in help_text
    assert "--config" not in help_text
    assert str(config) in run("init-config")
    content = (BACKEND / "core" / ".env.example").read_text()
    config.write_text(
        content + f"\nDATA_DIR={backend / 'data'}\nSITE_NAME=CLI test site\nCPAMP_USAGE_DB=\n"
    )
    original = config.read_bytes()
    assert str(config) in run("init-config")
    assert config.read_bytes() == original
    assert not (backend / "data").exists()
    assert "已创建管理员 admin" in run("create-admin", "admin", "--password", "first-password")
    assert "设为管理员" in run("create-admin", "admin")
    assert "已重置" in run("reset-password", "admin", "--password", "second-password")
    assert "12.5000" in run("credit", "admin", "12.5", "--note", "CLI test")
    codes = run(
        "gen-codes", "--amount", "5", "--count", "2", "--batch", "CLI", "--expires-days", "30"
    ).splitlines()
    assert len(codes) == 2 and codes[0] != codes[1]
    gifts = run("gen-codes", "--amount", "7", "--type", "gift").splitlines()
    assert len(gifts) == 1
    conn = connect(backend / "data" / "portal.sqlite")
    try:
        user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
        assert user["balance_micro"] == 12500000
        assert verify_password("second-password", user["password_hash"])
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM redeem_codes WHERE batch = 'CLI' AND type = 'recharge'"
            ).fetchone()[0]
            == 2
        )
        gift = conn.execute("SELECT * FROM redeem_codes WHERE code = ?", (gifts[0],)).fetchone()
        assert gift["type"] == "gift" and gift["amount_micro"] == 7000000
        assert conn.execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)
    finally:
        conn.close()
