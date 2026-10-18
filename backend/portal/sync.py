"""Background worker.

1. Bills usage: reads new rows from CPA Manager Plus' usage_events table
   (read-only), matches api_key_hash = sha256(api key) to portal keys, prices
   each request and deducts it from the owner's balance.
2. Syncs keys: makes CLIProxyAPI's client api-keys list contain exactly the
   portal keys that may currently be used (active, not expired, under quota,
   owner has balance). Keys the portal does not know about are never touched.
"""
import logging
import os
import pathlib
import sqlite3
import threading
import time

from . import billing
from .cpa import CPAError
from .db import get_setting, now_ms, set_setting, transaction

log = logging.getLogger("portal.sync")

EVENT_COLUMNS = [
    "id", "event_hash", "timestamp_ms", "model", "requested_model", "endpoint", "path",
    "api_key_hash", "input_tokens", "output_tokens", "reasoning_tokens", "cached_tokens",
    "cache_read_tokens", "cache_creation_tokens", "normalized_uncached_input_tokens",
    "normalized_cache_read_tokens", "normalized_cache_creation_tokens", "total_tokens",
    "failed", "latency_ms", "stream",
]
REQUIRED_COLUMNS = {"id", "event_hash", "timestamp_ms", "model", "api_key_hash"}

# Events stamped earlier than this before a key was created are never billed to it.
KEY_CLOCK_SKEW_MS = 5 * 60 * 1000
PRICE_REFRESH_SECONDS = 300
BULK_SYNC_THRESHOLD = 3

DESIRED_KEYS_SQL = """
SELECT k.key FROM api_keys k JOIN users u ON u.id = k.user_id
WHERE k.status = 'active' AND u.status = 'active' AND u.balance_micro > ?
  AND (k.expires_at IS NULL OR k.expires_at > ?)
  AND (k.quota_micro IS NULL OR k.used_micro < k.quota_micro)
"""


def _int(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def normalize_tokens(row):
    """Return (uncached_input, cache_read, cache_write, output, reasoning, total)."""
    output = _int(row["output_tokens"])
    reasoning = _int(row["reasoning_tokens"])
    if row["normalized_uncached_input_tokens"] is not None:
        uncached = _int(row["normalized_uncached_input_tokens"])
        cache_read = _int(row["normalized_cache_read_tokens"])
        cache_write = _int(row["normalized_cache_creation_tokens"])
    else:
        cache_read = max(_int(row["cache_read_tokens"]), _int(row["cached_tokens"]))
        cache_write = _int(row["cache_creation_tokens"])
        uncached = max(_int(row["input_tokens"]) - cache_read - cache_write, 0)
    total = _int(row["total_tokens"]) or (uncached + cache_read + cache_write + output)
    return uncached, cache_read, cache_write, output, reasoning, total


def open_cpamp(path):
    if not path or not os.path.exists(path):
        raise FileNotFoundError("未找到 CPA Manager Plus 数据库: %s" % path)
    uri = pathlib.Path(path).absolute().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = 1")
    return conn


class SyncWorker:
    def __init__(self, app):
        self.app = app
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._run_lock = threading.Lock()
        self._thread = None
        self._cpa_backoff_until = 0.0
        self._cpamp_prices = {}
        self._cpamp_prices_at = 0.0
        self.state = {
            "cpamp": {"ok": None, "error": None, "cursor": None, "last_run_at": None,
                      "last_event_at": None, "billed_events": 0},
            "cpa": {"enabled": False, "ok": None, "error": None, "last_sync_at": None,
                    "active_keys": 0, "added": 0, "removed": 0},
        }

    # -- lifecycle -----------------------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._loop, name="portal-sync", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def trigger(self):
        self._wake.set()

    def _loop(self):
        interval = max(3, int(self.app.cfg["cpamp"].get("sync_interval_seconds") or 15))
        while not self._stop.is_set():
            self._wake.clear()
            self.run_once()
            self._wake.wait(interval)

    def run_once(self):
        with self._run_lock:
            try:
                self.sync_usage()
            except Exception as exc:  # keep the worker alive whatever happens
                log.exception("usage sync failed")
                self.state["cpamp"].update(ok=False, error=str(exc))
            try:
                self.reconcile_keys()
            except Exception as exc:
                log.exception("key sync failed")
                self.state["cpa"].update(ok=False, error=str(exc))

    # -- pricing -------------------------------------------------------------------
    def cpamp_prices(self, src=None):
        """CPAMP official prices, cached for a few minutes."""
        if time.time() - self._cpamp_prices_at < PRICE_REFRESH_SECONDS and self._cpamp_prices_at:
            return self._cpamp_prices
        own = src is None
        try:
            if own:
                src = open_cpamp(self.app.cfg["cpamp"]["usage_db"])
            self._cpamp_prices = billing.load_cpamp_prices(src)
            self._cpamp_prices_at = time.time()
        except Exception:
            pass
        finally:
            if own and src is not None:
                src.close()
        return self._cpamp_prices

    def invalidate_prices(self):
        self._cpamp_prices_at = 0.0

    # -- usage billing -------------------------------------------------------------
    def sync_usage(self):
        state = self.state["cpamp"]
        state["last_run_at"] = now_ms()
        try:
            src = open_cpamp(self.app.cfg["cpamp"]["usage_db"])
        except Exception as exc:
            state.update(ok=False, error=str(exc))
            return
        conn = self.app.db()
        try:
            columns = {row[1] for row in src.execute("PRAGMA table_info(usage_events)")}
            missing = REQUIRED_COLUMNS - columns
            if missing:
                state.update(ok=False, error="usage_events 缺少字段: %s" % ", ".join(sorted(missing)))
                return
            select = ", ".join(c if c in columns else "NULL AS " + c for c in EVENT_COLUMNS)
            book = billing.build_price_book(conn, self.cpamp_prices(src), self.app.setting)

            cursor = get_setting(conn, "cpamp_cursor")
            if cursor is None:
                cursor = self._bootstrap_cursor(conn, src)
            keys = {
                row["key_hash"]: (row["id"], row["user_id"], row["created_at"])
                for row in conn.execute("SELECT id, user_id, key_hash, created_at FROM api_keys")
            }
            bill_failed = bool(self.app.cfg["pricing"].get("bill_failed_requests"))
            batch_size = max(100, int(self.app.cfg["cpamp"].get("batch_size") or 1000))
            billed = 0
            while True:
                rows = src.execute(
                    "SELECT %s FROM usage_events WHERE id > ? ORDER BY id LIMIT ?" % select,
                    (cursor, batch_size),
                ).fetchall()
                if not rows:
                    break
                billed += self._apply_batch(conn, rows, keys, book, bill_failed)
                cursor = rows[-1]["id"]
                if len(rows) < batch_size:
                    break
            state.update(ok=True, error=None, cursor=cursor)
            state["billed_events"] += billed
            if billed:
                log.info("billed %d new request(s), cursor=%s", billed, cursor)
        finally:
            conn.close()
            src.close()

    def _bootstrap_cursor(self, conn, src):
        """First run: start right before the first portal key existed."""
        first_key_ms = conn.execute("SELECT MIN(created_at) FROM api_keys").fetchone()[0]
        if first_key_ms is None:
            start = src.execute("SELECT COALESCE(MAX(id), 0) FROM usage_events").fetchone()[0]
        else:
            start = src.execute(
                "SELECT COALESCE(MAX(id), 0) FROM usage_events WHERE timestamp_ms < ?",
                (first_key_ms - KEY_CLOCK_SKEW_MS,),
            ).fetchone()[0]
        recent = src.execute(
            "SELECT model, MAX(timestamp_ms) AS last_ms, COUNT(*) AS calls FROM usage_events "
            "WHERE id > ? GROUP BY model",
            (max(start - 50000, 0),),
        ).fetchall()
        with transaction(conn):
            for row in recent:
                self._touch_model(conn, row["model"], row["last_ms"], row["calls"])
            set_setting(conn, "cpamp_cursor", start)
        log.info("usage cursor initialised at CPAMP event id %s", start)
        return start

    @staticmethod
    def _touch_model(conn, model, last_ms, calls):
        if not model:
            return
        conn.execute(
            "INSERT OR IGNORE INTO seen_models (model, last_seen_ms, calls) VALUES (?, ?, 0)",
            (model, last_ms or 0),
        )
        conn.execute(
            "UPDATE seen_models SET last_seen_ms = MAX(last_seen_ms, ?), calls = calls + ? "
            "WHERE model = ?",
            (last_ms or 0, calls, model),
        )

    def _apply_batch(self, conn, rows, keys, book, bill_failed):
        billed = 0
        models = {}
        last_event_at = self.state["cpamp"]["last_event_at"] or 0
        with transaction(conn):
            for row in rows:
                model = (row["model"] or row["requested_model"] or "").strip() or "unknown"
                ts = int(row["timestamp_ms"] or 0)
                last_event_at = max(last_event_at, ts)
                entry = models.setdefault(model, [0, 0])
                entry[0] = max(entry[0], ts)
                entry[1] += 1

                owner = keys.get((row["api_key_hash"] or "").strip().lower())
                if owner is None:
                    continue
                key_id, user_id, key_created_at = owner
                if ts and ts < key_created_at - KEY_CLOCK_SKEW_MS:
                    continue

                uncached, cache_read, cache_write, output, reasoning, total = normalize_tokens(row)
                failed = 1 if row["failed"] else 0
                price, source = book.resolve(model)
                cost = 0
                if price is not None and (bill_failed or not failed):
                    cost = price.cost_micro(uncached, cache_read, cache_write, output)
                inserted = conn.execute(
                    "INSERT OR IGNORE INTO usage_logs (event_hash, source_id, user_id, key_id, ts, "
                    "model, endpoint, input_tokens, cache_read_tokens, cache_write_tokens, "
                    "output_tokens, reasoning_tokens, total_tokens, cost_micro, failed, latency_ms, "
                    "stream, price_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (row["event_hash"], row["id"], user_id, key_id, ts, model,
                     row["endpoint"] or row["path"], uncached, cache_read, cache_write, output,
                     reasoning, total, cost, failed, row["latency_ms"],
                     None if row["stream"] is None else int(bool(row["stream"])), source),
                ).rowcount
                if inserted != 1:
                    continue
                billed += 1
                if cost:
                    conn.execute(
                        "UPDATE users SET balance_micro = balance_micro - ?, "
                        "total_spent_micro = total_spent_micro + ? WHERE id = ?",
                        (cost, cost, user_id),
                    )
                conn.execute(
                    "UPDATE api_keys SET used_micro = used_micro + ?, request_count = request_count + 1, "
                    "last_used_at = MAX(COALESCE(last_used_at, 0), ?) WHERE id = ?",
                    (cost, ts, key_id),
                )
            for model, (last_ms, calls) in models.items():
                self._touch_model(conn, model, last_ms, calls)
            set_setting(conn, "cpamp_cursor", rows[-1]["id"])
        self.state["cpamp"]["last_event_at"] = last_event_at or None
        return billed

    # -- CPA key sync --------------------------------------------------------------
    def reconcile_keys(self):
        state = self.state["cpa"]
        cpa = self.app.cpa
        state["enabled"] = bool(cpa.configured and self.app.cfg["cpa"].get("sync_keys", True))
        if not state["enabled"] or time.time() < self._cpa_backoff_until:
            return
        conn = self.app.db()
        try:
            min_balance = billing.to_micro(self.app.cfg.get("min_balance_to_call") or 0)
            desired = {row[0] for row in conn.execute(DESIRED_KEYS_SQL, (min_balance, now_ms()))}
            managed = {row[0] for row in conn.execute("SELECT key FROM api_keys")}
        finally:
            conn.close()
        try:
            current = cpa.list_api_keys()
            present = set(current)
            to_add = sorted(desired - present)
            to_remove = sorted({k for k in current if k in managed and k not in desired})
            if len(to_add) + len(to_remove) > BULK_SYNC_THRESHOLD:
                # Every PATCH/DELETE rewrites config.yaml and reloads CPA; batch large diffs.
                drop = set(to_remove)
                cpa.put_api_keys([k for k in current if k not in drop] + to_add)
            else:
                for key in to_add:
                    cpa.add_api_key(key)
                for key in to_remove:
                    cpa.remove_api_key(key)
        except CPAError as exc:
            # CPA bans an IP for 30 minutes after 5 bad management keys, and CPA Manager Plus
            # calls the same API from 127.0.0.1, so auth/config errors stop automatic retries
            # until an admin presses "立即同步" or the service restarts.
            if exc.status in (401, 403, 404):
                self._cpa_backoff_until = time.time() + 86400
                message = ("%s（已暂停自动重试，避免触发 CPA 封禁本机 IP；修正 config.json 后重启服务，"
                           "或在运营概况点击“立即同步”重试）" % exc)
            else:
                self._cpa_backoff_until = time.time() + 30
                message = str(exc)
            state.update(ok=False, error=message)
            log.warning("key sync failed: %s", exc)
            return
        state.update(ok=True, error=None, last_sync_at=now_ms(), active_keys=len(desired))
        if to_add or to_remove:
            state["added"] += len(to_add)
            state["removed"] += len(to_remove)
            log.info("CPA api-keys synced: +%d -%d", len(to_add), len(to_remove))

    def reset_backoff(self):
        self._cpa_backoff_until = 0.0
