"""Client for the nginx routing control endpoint (deploy/cpa-router/cpa_route.lua).

nginx serves it on a loopback-only port. GET returns the live routing state, POST
replaces the routing configuration. Both need the shared token header.
"""

import json
import urllib.error
import urllib.parse
import urllib.request


class RouterError(Exception):
    pass


class RouterClient:
    def __init__(self, control_url, token, timeout=3):
        self.base = (control_url or "").strip().rstrip("/")
        self.token = (token or "").strip()
        self.timeout = timeout
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def configured(self):
        return bool(self.base and self.token)

    def status(self):
        return self._call(None)

    def push(self, config):
        """Replace nginx's routing configuration and return the resulting live state."""
        return self._call(urllib.parse.urlencode({"config": config}).encode("utf-8"))

    def _call(self, body):
        request = urllib.request.Request(
            self.base + "/routing", data=body, method="GET" if body is None else "POST"
        )
        request.add_header("X-Router-Token", self.token)
        if body is not None:
            request.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:200].decode("utf-8", "replace")
            raise RouterError("nginx 分流接口返回 HTTP %d: %s" % (exc.code, detail))
        except (urllib.error.URLError, OSError) as exc:
            raise RouterError("无法连接 nginx 分流接口: %s" % getattr(exc, "reason", exc))
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise RouterError("nginx 分流接口返回了非 JSON 内容")
        if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
            raise RouterError("nginx 分流接口返回的数据格式不正确")
        return data
