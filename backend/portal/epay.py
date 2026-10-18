"""易支付 (EPay) protocol: page-jump submit + MD5-signed async notify.

Compatible with the common "彩虹易支付" style gateways: submit.php with
pid/type/out_trade_no/notify_url/return_url/name/money, signed by sorting the
non-empty params (except sign/sign_type), joining as k=v&k=v and appending KEY.
"""
import hashlib
import hmac
import urllib.parse


def sign(params, key):
    items = sorted(
        (k, str(v)) for k, v in params.items()
        if k not in ("sign", "sign_type") and v is not None and str(v) != ""
    )
    payload = "&".join("%s=%s" % (k, v) for k, v in items) + key
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def verify(params, key):
    received = str(params.get("sign") or "").lower()
    return bool(received) and hmac.compare_digest(received, sign(params, key))


def submit_url(gateway):
    gateway = gateway.strip()
    if gateway.endswith(".php"):
        return gateway
    return gateway.rstrip("/") + "/submit.php"


def build_pay_url(conf, channel, order_no, money, name, notify_url, return_url, site_name=""):
    params = {
        "pid": conf["pid"],
        "type": channel,
        "out_trade_no": order_no,
        "notify_url": notify_url,
        "return_url": return_url,
        "name": name,
        "money": money,
        "sitename": site_name,
    }
    params["sign"] = sign(params, conf["key"])
    params["sign_type"] = "MD5"
    return submit_url(conf["gateway"]) + "?" + urllib.parse.urlencode(params)
