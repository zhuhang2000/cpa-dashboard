"""Minimal client for the CLIProxyAPI management API (client api-keys only)."""
import json
import urllib.error
import urllib.parse
import urllib.request


class CPAError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class CPAClient:
    def __init__(self, base_url, management_key, timeout=8):
        base = (base_url or "").strip().rstrip("/")
        if base.endswith("/v0/management"):
            base = base[: -len("/v0/management")]
        self.base = base
        self.key = (management_key or "").strip()
        self.timeout = timeout
        # Never route management traffic through an http_proxy from the environment.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def configured(self):
        return bool(self.base and self.key)

    def _call(self, method, path, body=None, query=None):
        url = self.base + "/v0/management" + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Authorization", "Bearer " + self.key)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:200].decode("utf-8", "replace")
            raise CPAError("CPA 管理接口返回 HTTP %d: %s" % (exc.code, detail), exc.code)
        except (urllib.error.URLError, OSError) as exc:
            raise CPAError("无法连接 CPA 管理接口: %s" % getattr(exc, "reason", exc))
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            raise CPAError("CPA 管理接口返回了非 JSON 内容")

    def list_api_keys(self):
        data = self._call("GET", "/api-keys") or {}
        return [k for k in (data.get("api-keys") or []) if isinstance(k, str)]

    def add_api_key(self, key):
        # PATCH {old,new} replaces "old" when present and appends "new" otherwise,
        # so old == new is an atomic, idempotent "ensure present".
        self._call("PATCH", "/api-keys", {"old": key, "new": key})

    def remove_api_key(self, key):
        self._call("DELETE", "/api-keys", query={"value": key})

    def put_api_keys(self, keys):
        self._call("PUT", "/api-keys", list(keys))
