"""Schedule usage ingestion and reconcile portal keys with CLIProxyAPI.

The worker owns runtime state, retries and external-call orchestration. Portal
database operations belong to services; CPAMP reads belong to its adapter.
"""

import logging
import threading
import time

from core.db import now_ms
from integrations import cpamp
from integrations.cpa import CPAError
from services import api_keys, pricing, usage

log = logging.getLogger("portal.sync")
PRICE_REFRESH_SECONDS = 300
BULK_SYNC_THRESHOLD = 3


class SyncWorker:
    def __init__(self, runtime):
        self.runtime = runtime
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._run_lock = threading.Lock()
        self._thread = None
        self._cpa_backoff_until = 0.0
        self._cpamp_prices = {}
        self._cpamp_prices_at = 0.0
        self.state = {
            "cpamp": {
                "ok": None,
                "error": None,
                "cursor": None,
                "last_run_at": None,
                "last_event_at": None,
                "billed_events": 0,
            },
            "cpa": {
                "enabled": False,
                "ok": None,
                "error": None,
                "last_sync_at": None,
                "active_keys": 0,
                "added": 0,
                "removed": 0,
            },
        }

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="portal-sync", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join()

    def trigger(self):
        self._wake.set()

    def run_once(self):
        with self._run_lock:
            try:
                self.sync_usage()
            except Exception as exc:
                log.exception("usage sync failed")
                self.state["cpamp"].update(ok=False, error=str(exc))
            try:
                self.reconcile_keys()
            except Exception as exc:
                log.exception("key sync failed")
                self.state["cpa"].update(ok=False, error=str(exc))

    def cpamp_prices(self, src=None):
        """Return official prices cached for a few minutes."""
        if time.time() - self._cpamp_prices_at < PRICE_REFRESH_SECONDS and self._cpamp_prices_at:
            return self._cpamp_prices
        own = src is None
        try:
            if own:
                src = cpamp.open_database(self.runtime.cfg["cpamp"]["usage_db"])
            self._cpamp_prices = pricing.prices_from_external(cpamp.load_prices(src))
            self._cpamp_prices_at = time.time()
        except Exception:
            pass
        finally:
            if own and src is not None:
                src.close()
        return self._cpamp_prices

    def invalidate_prices(self):
        self._cpamp_prices_at = 0.0

    def sync_usage(self):
        state = self.state["cpamp"]
        state["last_run_at"] = now_ms()
        try:
            src = cpamp.open_database(self.runtime.cfg["cpamp"]["usage_db"])
        except Exception as exc:
            state.update(ok=False, error=str(exc))
            return
        conn = self.runtime.db()
        try:
            try:
                columns = cpamp.usage_columns(src)
            except ValueError as exc:
                state.update(ok=False, error=str(exc))
                return
            book = pricing.build_price_book(conn, self.cpamp_prices(src), self.runtime.settings.get)
            cursor = usage.get_cursor(conn)
            if cursor is None:
                first_key_ms = api_keys.first_created_at(conn)
                before_ms = None if first_key_ms is None else first_key_ms - usage.KEY_CLOCK_SKEW_MS
                cursor = cpamp.initial_cursor(src, before_ms)
                usage.initialize_cursor(conn, cursor, cpamp.recent_models(src, cursor))
                log.info("usage cursor initialised at CPAMP event id %s", cursor)
            keys = api_keys.billing_owners(conn)
            bill_failed = self.runtime.cfg["pricing"]["bill_failed_requests"]
            batch_size = self.runtime.cfg["cpamp"]["batch_size"]
            billed = 0
            while True:
                rows = cpamp.read_events(src, cursor, batch_size, columns)
                if not rows:
                    break
                count, last_event_at = usage.apply_batch(
                    conn,
                    rows,
                    keys,
                    book,
                    bill_failed,
                    state["last_event_at"],
                )
                state["last_event_at"] = last_event_at
                billed += count
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

    def reconcile_keys(self):
        state = self.state["cpa"]
        cpa = self.runtime.cpa
        state["enabled"] = cpa.configured and self.runtime.cfg["cpa"]["sync_keys"]
        if not state["enabled"] or time.time() < self._cpa_backoff_until:
            return
        conn = self.runtime.db()
        try:
            desired, managed = api_keys.desired_and_managed(conn, self.runtime.cfg)
        finally:
            conn.close()
        try:
            current = cpa.list_api_keys()
            present = set(current)
            to_add = sorted(desired - present)
            to_remove = sorted({key for key in current if key in managed and key not in desired})
            if len(to_add) + len(to_remove) > BULK_SYNC_THRESHOLD:
                drop = set(to_remove)
                cpa.put_api_keys([key for key in current if key not in drop] + to_add)
            else:
                for key in to_add:
                    cpa.add_api_key(key)
                for key in to_remove:
                    cpa.remove_api_key(key)
        except CPAError as exc:
            # Avoid CPA's IP ban after repeated management authentication errors.
            if exc.status in (401, 403, 404):
                self._cpa_backoff_until = time.time() + 86400
                message = (
                    "%s（已暂停自动重试，避免触发 CPA 封禁本机 IP；修正 config.json 后重启服务，"
                    "或在运营概况点击“立即同步”重试）" % exc
                )
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

    def _loop(self):
        interval = self.runtime.cfg["cpamp"]["sync_interval_seconds"]
        while not self._stop.is_set():
            self._wake.clear()
            self.run_once()
            self._wake.wait(interval)
