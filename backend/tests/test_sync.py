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
from core.db import MIGRATIONS, connect, get_setting, init_db, now_ms, set_setting
from integrations import cpamp
from integrations.cpa import CPAError
from runtime.sync import Node, SyncWorker
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


class UnreachableCPA:
    configured = True

    def __init__(self):
        self.calls = 0

    def list_api_keys(self):
        self.calls += 1
        raise CPAError("无法连接 CPA 管理接口: timed out")


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
        self.node = Node("node1", FakeCPA(), self.source_path)
        self.runtime = SimpleNamespace(
            cfg=self.cfg, db=lambda: connect(self.path), nodes=[self.node]
        )
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
            self.assertEqual(get_setting(conn, "cpamp_cursor:node1"), 4)
            # Replaying already-seen source rows also cannot double charge.
            set_setting(conn, "cpamp_cursor:node1", 1)
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

    def test_long_context_tier_loads_from_cpamp_and_bills_long_requests(self):
        src = sqlite3.connect(self.source_path)
        try:
            src.executescript("""
                CREATE TABLE model_price_context_tiers (
                    model TEXT, threshold_tokens INTEGER, prompt_per_1m REAL, completion_per_1m REAL
                );
                INSERT INTO model_price_context_tiers VALUES ('test-model', 1500, 4, 6);
                INSERT INTO model_price_context_tiers VALUES ('unpriced-model', 1500, 4, 6);
            """)
            src.execute(
                "INSERT INTO usage_events VALUES (?,?,?,?,?,?,?,?)",
                (5, "long", self.timestamp + 3, "test-model", self.key_hash, 2000, 100, 0),
            )
            src.commit()
        finally:
            src.close()
        src = cpamp.open_database(self.source_path)
        try:
            tier = {"threshold": 1500, "input": 4, "output": 6, "cache_read": 0.4, "cache_write": 5}
            self.assertEqual(cpamp.load_prices(src)["test-model"]["tiers"], [tier])
            self.assertNotIn("unpriced-model", cpamp.load_prices(src))
        finally:
            src.close()
        self.worker.sync_usage()
        conn = connect(self.path)
        try:
            costs = dict(conn.execute("SELECT event_hash, cost_micro FROM usage_logs").fetchall())
        finally:
            conn.close()
        # 1000 input tokens stay on the base price (2, 4); 2000 cross the tier (4, 6).
        self.assertEqual((costs["billed"], costs["long"]), (2400, 8600))

    def test_failed_batch_rolls_back_usage_balance_key_models_and_cursor(self):
        conn = connect(self.path)
        try:
            set_setting(conn, "cpamp_cursor:node1", 1)
        finally:
            conn.close()
        # Fail at the final cursor write, after all other mutations have occurred.
        with patch("services.usage.set_setting", side_effect=RuntimeError("cursor write failed")):
            with self.assertRaisesRegex(RuntimeError, "cursor write failed"):
                self.worker.sync_node_usage(self.node)
        conn = connect(self.path)
        try:
            self.assertEqual(get_setting(conn, "cpamp_cursor:node1"), 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM usage_logs").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM seen_models").fetchone()[0], 0)
            user = conn.execute("SELECT balance_micro,total_spent_micro FROM users").fetchone()
            key = conn.execute(
                "SELECT used_micro,request_count,last_used_at FROM api_keys"
            ).fetchone()
            self.assertEqual(tuple(user), (10000000, 0))
            self.assertEqual(tuple(key), (0, 0, None))
            self.assertIsNone(self.worker.state["node1"]["cpamp"]["last_event_at"])
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
                self.assertEqual(set(self.node.cpa.keys), owned | {"unmanaged-external-key"})
                conn = connect(self.path)
                try:
                    conn.execute("UPDATE users SET status = 'banned'")
                finally:
                    conn.close()
                self.worker.reconcile_keys()
                self.assertEqual(self.node.cpa.keys, ["unmanaged-external-key"])

    def add_node(self, node_id, events=None, cpa=None):
        """Append a node; events create its CPAMP database, None leaves it missing."""
        path = os.path.join(self.temp.name, node_id + ".sqlite")
        if events is not None:
            src = sqlite3.connect(path)
            try:
                src.execute(
                    "CREATE TABLE usage_events (id INTEGER PRIMARY KEY, event_hash TEXT, "
                    "timestamp_ms INTEGER, model TEXT, api_key_hash TEXT, input_tokens INTEGER, "
                    "output_tokens INTEGER, failed INTEGER)"
                )
                src.executemany("INSERT INTO usage_events VALUES (?,?,?,?,?,?,?,?)", events)
                src.commit()
            finally:
                src.close()
        node = Node(node_id, cpa or FakeCPA(), path)
        self.runtime.nodes.append(node)
        return node

    def new_worker(self):
        worker = SyncWorker(self.runtime)
        self.addCleanup(worker.stop)
        return worker

    def test_every_node_bills_the_same_user_with_its_own_cursor(self):
        # Node 2 numbers its events from 1 as well and has no price table of its own.
        self.add_node(
            "node2",
            [
                (1, "node2-a", self.timestamp + 10, "test-model", self.key_hash, 1000, 100, 0),
                (2, "node2-b", self.timestamp + 11, "test-model", self.key_hash, 1000, 100, 0),
            ],
        )
        worker = self.new_worker()
        worker.sync_usage()
        worker.sync_usage()
        conn = connect(self.path)
        try:
            hashes = {row[0] for row in conn.execute("SELECT event_hash FROM usage_logs")}
            balance = conn.execute("SELECT balance_micro FROM users").fetchone()[0]
            self.assertEqual(hashes, {"billed", "failed", "node2-a", "node2-b"})
            self.assertEqual(balance, 10000000 - 3 * 2400)
            self.assertEqual(get_setting(conn, "cpamp_cursor:node1"), 4)
            self.assertEqual(get_setting(conn, "cpamp_cursor:node2"), 2)
        finally:
            conn.close()
        self.assertEqual(worker.state["node2"]["cpamp"]["billed_events"], 2)

    def test_an_unreadable_node_does_not_stop_the_nodes_after_it(self):
        self.add_node("node2")
        self.add_node(
            "node3",
            [(1, "node3-a", self.timestamp + 10, "test-model", self.key_hash, 1000, 100, 0)],
        )
        worker = self.new_worker()
        worker.run_once()
        self.assertIs(worker.state["node2"]["cpamp"]["ok"], False)
        self.assertIn("node2.sqlite", worker.state["node2"]["cpamp"]["error"])
        self.assertIs(worker.state["node3"]["cpamp"]["ok"], True)
        conn = connect(self.path)
        try:
            hashes = {row[0] for row in conn.execute("SELECT event_hash FROM usage_logs")}
        finally:
            conn.close()
        self.assertEqual(hashes, {"billed", "failed", "node3-a"})

    def test_keys_reach_every_node_and_only_a_failing_node_backs_off(self):
        down = self.add_node("node2", cpa=UnreachableCPA())
        node3 = self.add_node("node3")
        worker = self.new_worker()
        worker.reconcile_keys()
        worker.reconcile_keys()
        for node in (self.node, node3):
            self.assertEqual(set(node.cpa.keys), {self.key, "unmanaged-external-key"})
            self.assertIs(worker.state[node.id]["cpa"]["ok"], True)
        self.assertIs(worker.state["node2"]["cpa"]["ok"], False)
        self.assertEqual(down.cpa.calls, 1)
        worker.reset_backoff()
        worker.reconcile_keys()
        self.assertEqual(down.cpa.calls, 2)

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


def test_migration_moves_the_existing_cursor_to_node1(tmp_path):
    path = str(tmp_path / "portal.sqlite")
    conn = connect(path)
    try:
        conn.executescript("\n".join(MIGRATIONS[:6]) + "\nPRAGMA user_version = 6;")
        set_setting(conn, "cpamp_cursor", 42)
    finally:
        conn.close()
    init_db(path)
    conn = connect(path)
    try:
        assert get_setting(conn, "cpamp_cursor") is None
        assert get_setting(conn, "cpamp_cursor:node1") == 42
    finally:
        conn.close()
