"""Admin-editable settings and their cache, initially read from config/config.json."""

import threading

from core.db import get_setting, set_setting

# Settings an admin may change at runtime: name -> (type, path in config.json).
EDITABLE_SETTINGS = {
    "site_name": (str, ("site_name",)),
    "public_api_base": (str, ("public_api_base",)),
    "announcement": (str, None),
    "allow_register": (bool, ("allow_register",)),
    "signup_bonus": (float, ("signup_bonus",)),
    "use_cpamp_prices": (bool, ("pricing", "use_cpamp_prices")),
    "cpamp_price_multiplier": (float, ("pricing", "cpamp_price_multiplier")),
    "default_input_price": (float, ("pricing", "default_input_price")),
    "default_output_price": (float, ("pricing", "default_output_price")),
}


class RuntimeSettings:
    def __init__(self, cfg, connect):
        self.cfg = cfg
        self.connect = connect
        self._runtime = None
        self._runtime_lock = threading.Lock()

    # -- runtime settings ----------------------------------------------------------
    def _runtime_settings(self):
        with self._runtime_lock:
            if self._runtime is None:
                conn = self.connect()
                try:
                    self._runtime = get_setting(conn, "runtime_settings", {}) or {}
                finally:
                    conn.close()
            return self._runtime

    def get(self, name):
        runtime = self._runtime_settings()
        if name in runtime:
            return runtime[name]
        kind, path = EDITABLE_SETTINGS[name]
        if path is None:
            return kind()
        value = self.cfg
        for part in path:
            value = value.get(part) if isinstance(value, dict) else None
        return kind() if value is None else value

    def all(self):
        return {name: self.get(name) for name in EDITABLE_SETTINGS}

    def update(self, values):
        clean = {}
        for name, value in values.items():
            if name not in EDITABLE_SETTINGS:
                continue
            kind = EDITABLE_SETTINGS[name][0]
            if kind is bool:
                clean[name] = bool(value)
            elif kind is float:
                number = float(value)
                if number < 0 or number != number:
                    raise ValueError("%s 不能为负数" % name)
                clean[name] = number
            else:
                clean[name] = str(value or "").strip()
        with self._runtime_lock:
            conn = self.connect()
            try:
                current = get_setting(conn, "runtime_settings", {}) or {}
                current.update(clean)
                set_setting(conn, "runtime_settings", current)
            finally:
                conn.close()
            self._runtime = current
        return self.all()
