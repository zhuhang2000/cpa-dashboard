"""Password hashing, random secrets and a small in-memory rate limiter."""
import base64
import hashlib
import hmac
import secrets
import string
import threading
import time

PBKDF2_ITERATIONS = 600000
_KEY_ALPHABET = string.ascii_letters + string.digits
# Redeem codes avoid look-alike characters (0/O, 1/I/L).
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _b64(data):
    return base64.b64encode(data).decode("ascii").rstrip("=")


def _unb64(text):
    return base64.b64decode(text + "=" * (-len(text) % 4))


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256$%d$%s$%s" % (PBKDF2_ITERATIONS, _b64(salt), _b64(digest))


def verify_password(password, encoded):
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _unb64(salt), int(iterations)
        )
        return hmac.compare_digest(digest, _unb64(expected))
    except (ValueError, TypeError):
        return False


def sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_session_token():
    return secrets.token_urlsafe(32)


def new_api_key(prefix="sk-"):
    return prefix + "".join(secrets.choice(_KEY_ALPHABET) for _ in range(48))


def new_redeem_code():
    raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(16))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


class RateLimiter:
    """Sliding-window counters keyed by arbitrary strings (IP, user id, ...)."""

    def __init__(self):
        self._hits = {}
        self._lock = threading.Lock()
        self._last_sweep = time.time()

    def _recent(self, key, window, now):
        hits = [t for t in self._hits.get(key, ()) if now - t < window]
        if hits:
            self._hits[key] = hits
        else:
            self._hits.pop(key, None)
        return hits

    def count(self, key, window):
        with self._lock:
            return len(self._recent(key, window, time.time()))

    def add(self, key):
        now = time.time()
        with self._lock:
            self._hits.setdefault(key, []).append(now)
            if now - self._last_sweep > 600:
                self._last_sweep = now
                for stale in [k for k, v in self._hits.items() if now - v[-1] > 3600]:
                    del self._hits[stale]

    def allow(self, key, limit, window):
        """Record a hit and return False when the limit is already reached."""
        now = time.time()
        with self._lock:
            hits = self._recent(key, window, now)
            if len(hits) >= limit:
                return False
            self._hits.setdefault(key, []).append(now)
            return True

    def reset(self, key):
        with self._lock:
            self._hits.pop(key, None)
