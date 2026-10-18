"""Exercise real SQLite ingestion and the worker's external-key reconciliation."""

import copy
import os
import sqlite3
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.config import load_config
from core.db import connect, get_setting, init_db, now_ms, set_setting
from integrations import cpamp
from runtime.sync import SyncWorker
from services import api_keys
from services.settings import RuntimeSettings


class FakeCPA:
    configured = True

    def __init__(self):
        self.keys = ["unmanaged-external-key"]

    def list_api_keys(self):
        return list(self.keys)

    def put_api_keys(self, keys):
        self.keys = list(keys)

    def add_api_key(self, key):
        self.keys.append(key)

    def remove_api_key(self, key):
        self.keys.remove(key)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = os.path.join(self.temp.name, "portal.sqlite")
        self.source_path = os.path.join(self.temp.name, "cpamp.sqlite")
        init_db(self.path)
        self.cfg = copy.deepcopy(load_config())
        self.cfg["cpamp"]["usage_db"] = self.source_path
        self.cfg["cpa"]["sync_keys"] = True
        self.runtime = SimpleNamespace(cfg=self.cfg, db=lambda: connect(self.path), cpa=FakeCPA())
        self.runtime.settings = RuntimeSettings(self.cfg, self.runtime.db)
        self.worker = SyncWorker(self.runtime)
        self.addCleanup(self.worker.stop)
        self.timestamp = now_ms()
        conn = connect(self.path)
        try:
            self.user_id = conn.execute(
                "INSERT INTO users (username,password_hash,balance_micro,created_at) VALUES (?,?,?,?)",
                ("sync-user", "unused", 10000000, self.timestamp - 60000),
            ).lastrowid
            key = api_keys.create(conn, self.cfg, self.user_id, {"name": "sync-test"})
            self.key_id, self.key, self.key_hash = key["id"], key["key"], key["key_hash"]
        finally:
            conn.close()
        src = sqlite3.connect(self.source_path)
        try:
            src.executescript("""
                CREATE TABLE usage_events (
                    id INTEGER PRIMARY KEY, event_hash TEXT, timestamp_ms INTEGER,
                    model TEXT, api_key_hash TEXT, input_tokens INTEGER,
                    output_tokens INTEGER, failed INTEGER
                );
                CREATE TABLE model_prices (
                    model TEXT, prompt_per_1m REAL, completion_per_1m REAL
                );
                INSERT INTO model_prices VALUES ('test-model', 2, 4);
            """)
            src.executemany(
                "INSERT INTO usage_events VALUES (?,?,?,?,?,?,?,?)",
                [
                    (
                        1,
                        "before-key",
                        self.timestamp - 3600000,
                        "test-model",
                        self.key_hash,
                        1000,
                        100,
                        0,
                    ),
                    (2, "billed", self.timestamp, "test-model", self.key_hash, 1000, 100, 0),
                    (3, "failed", self.timestamp + 1, "test-model", self.key_hash, 1000, 100, 1),
                    (4, "foreign", self.timestamp + 2, "test-model", "unknown-key", 1000, 100, 0),
                ],
            )
            src.commit()
        finally:
            src.close()

    def test_real_cpamp_ingestion_is_read_only_and_charges_once(self):
        self.worker.sync_usage()
        self.worker.sync_usage()
        conn = connect(self.path)
        try:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (self.user_id,)).fetchone()
            key = api_keys.get_owned(conn, self.user_id, self.key_id)
            logs = conn.execute(
                "SELECT event_hash,cost_micro,failed FROM usage_logs ORDER BY id"
            ).fetchall()
            self.assertEqual([tuple(row) for row in logs], [("billed", 2400, 0), ("failed", 0, 1)])
            self.assertEqual(user["balance_micro"], 10000000 - 2400)
            self.assertEqual(user["total_spent_micro"], 2400)
            self.assertEqual((key["used_micro"], key["request_count"]), (2400, 2))
            self.assertEqual(get_setting(conn, "cpamp_cursor"), 4)
            # Replaying already-seen source rows also cannot double charge.
            set_setting(conn, "cpamp_cursor", 1)
        finally:
            conn.close()
        self.worker.sync_usage()
        conn = connect(self.path)
        try:
            self.assertEqual(conn.execute("SELECT balance_micro FROM users").fetchone()[0], 9997600)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM usage_logs").fetchone()[0], 2)
        finally:
            conn.close()
        src = cpamp.open_database(self.source_path)
        try:
            self.assertEqual(src.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], 4)
            with self.assertRaises(sqlite3.OperationalError):
                src.execute("DELETE FROM usage_events")
        finally:
            src.close()

    def test_failed_batch_rolls_back_usage_balance_key_models_and_cursor(self):
        conn = connect(self.path)
        try:
            set_setting(conn, "cpamp_cursor", 1)
        finally:
            conn.close()
        # Fail at the final cursor write, after all other mutations have occurred.
        with patch("services.usage.set_setting", side_effect=RuntimeError("cursor write failed")):
            with self.assertRaisesRegex(RuntimeError, "cursor write failed"):
                self.worker.sync_usage()
        conn = connect(self.path)
        try:
            self.assertEqual(get_setting(conn, "cpamp_cursor"), 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM usage_logs").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM seen_models").fetchone()[0], 0)
            user = conn.execute("SELECT balance_micro,total_spent_micro FROM users").fetchone()
            key = conn.execute(
                "SELECT used_micro,request_count,last_used_at FROM api_keys"
            ).fetchone()
            self.assertEqual(tuple(user), (10000000, 0))
            self.assertEqual(tuple(key), (0, 0, None))
            self.assertIsNone(self.worker.state["cpamp"]["last_event_at"])
        finally:
            conn.close()

    def test_reconcile_keeps_external_keys_and_removes_banned_users_keys(self):
        for bulk in (False, True):
            with self.subTest(bulk=bulk):
                conn = connect(self.path)
                try:
                    conn.execute("UPDATE users SET status = 'active'")
                    if bulk:
                        for index in range(3):
                            api_keys.create(
                                conn, self.cfg, self.user_id, {"name": "bulk-%d" % index}
                            )
                    owned = {row[0] for row in conn.execute("SELECT key FROM api_keys")}
                finally:
                    conn.close()
                self.worker.reconcile_keys()
                self.assertEqual(set(self.runtime.cpa.keys), owned | {"unmanaged-external-key"})
                conn = connect(self.path)
                try:
                    conn.execute("UPDATE users SET status = 'banned'")
                finally:
                    conn.close()
                self.worker.reconcile_keys()
                self.assertEqual(self.runtime.cpa.keys, ["unmanaged-external-key"])

    def test_lifecycle_joins_thread_and_can_restart(self):
        started = threading.Event()

        def loop():
            started.set()
            self.worker._stop.wait()

        with patch.object(self.worker, "_loop", side_effect=loop):
            self.worker.start()
            self.assertTrue(started.wait(2))
            first = self.worker._thread
            self.worker.start()
            self.assertIs(self.worker._thread, first)
            self.worker.stop()
            self.assertFalse(first.is_alive())
            started.clear()
            self.worker.start()
            self.assertTrue(started.wait(2))
            self.assertIsNot(self.worker._thread, first)
            self.worker.stop()
            self.assertFalse(self.worker._thread.is_alive())


if __name__ == "__main__":
    unittest.main()
