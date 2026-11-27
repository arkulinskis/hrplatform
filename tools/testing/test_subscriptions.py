"""Tests for the monthly plan kit (server_code/Subscriptions.py). Same file in every app (tools/payments_rollout.py).

    python tools/testing/test_subscriptions.py      -> prints ALL OK, or the first failure
"""
import datetime as dt
import hashlib
import hmac
import importlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
_tmp = pathlib.Path(tempfile.mkdtemp())
shutil.copytree(PROJECT / "server_code", _tmp / "app")
(_tmp / "app" / "__init__.py").write_text("")
os.environ["ANVIL_APP_YAML"] = str(PROJECT / "anvil.yaml")
sys.path[:0] = [str(HERE / "mock"), str(_tmp)]
import anvil.http  # noqa: E402
import anvil.secrets  # noqa: E402
import anvil.server  # noqa: E402
import anvil.users  # noqa: E402
from anvil.tables import app_tables as T  # noqa: E402

S = importlib.import_module("app.Subscriptions")
FAKE = {"subs": {}}
END = int(time.time()) + 14 * 86400


def sub_obj(sid, status="trialing", qty=1):
    return {"id": sid, "status": status, "customer": "cus_1", "current_period_end": END,
            "items": {"data": [{"id": "si_1", "quantity": qty, "price": {"recurring": {"interval": "month"}}}]}}


def fake(url, method, data):
    path = url.split("/v1/", 1)[1]
    form = dict(urllib.parse.parse_qsl(data or ""))
    if path == "checkout/sessions" and method == "POST":
        FAKE["checkout"] = form
        return {"id": "cs_test_s1", "url": "https://checkout.stripe.com/c/pay/cs_test_s1"}
    if path.startswith("checkout/sessions/"):
        FAKE["subs"].setdefault("sub_1", sub_obj("sub_1", qty=int(FAKE["checkout"].get("line_items[0][quantity]", 1))))
        return {"id": "cs_test_s1", "status": "complete", "client_reference_id": FAKE["checkout"]["client_reference_id"],
                "customer_details": {"email": "boss@example.com"}, "metadata": {"sub": "1"}, "subscription": FAKE["subs"]["sub_1"]}
    if path.startswith("subscriptions/"):
        sid = path.split("/")[1].split("?")[0]
        if method == "DELETE":
            FAKE["subs"][sid]["status"] = "canceled"
        elif method == "POST" and "items[0][quantity]" in form:
            FAKE["subs"][sid]["items"]["data"][0]["quantity"] = int(form["items[0][quantity]"])
        return FAKE["subs"][sid]
    if path == "billing_portal/sessions":
        return {"url": "https://billing.stripe.com/p/session/x"}
    raise anvil.http.HttpError(404, path)


anvil.http.REPLIES["https://api.stripe.com/v1/"] = fake


def as_user(row):
    anvil.users.CURRENT[0] = row
    if hasattr(anvil.server.session, "use"):
        anvil.server.session.use(row.get_id() if row is not None else None)


def check(c, what):
    if not c:
        raise AssertionError(what)


def main():
    boss = T.users.add_row(email="boss@example.com", enabled=True, is_admin=False)
    admin = T.users.add_row(email="admin@example.com", enabled=True, is_admin=True)
    anvil.secrets.SECRETS.clear()
    as_user(boss)
    st = S.subscription_status()
    json.dumps(st)
    check(st["gate"] is False and st["active"] and st["state"] == "free", "free before the key")
    check(S.seats_ok(boss, 500), "no seat limit while free")

    anvil.secrets.SECRETS["stripe_secret_key"] = "rk_test_1"
    check(not S.active(boss) and S.subscription_status()["state"] == "none", "locked with the key")
    check(S.active(admin), "admins always")
    S.CFG.PER_SEAT, S.CFG.FREE_SEATS, S.CFG.MIN_SEATS = True, 5, 3
    check(S.seats_ok(boss, 5) and not S.seats_ok(boss, 6), "free seats only")

    r = S.subscription_checkout("year", 8)
    check(r["ok"], "checkout: %r" % r)
    f = FAKE["checkout"]
    check(f["mode"] == "subscription" and f["line_items[0][price_data][recurring][interval]"] == "year", "yearly")
    check(f["line_items[0][quantity]"] == "8" and f["subscription_data[trial_period_days]"] == "14", "seats + trial")
    check(S.subscription_confirm("nope")["ok"] is False, "bad id")
    c = S.subscription_confirm("cs_test_s1")
    check(c["ok"] and c["status"] == "trialing" and c["active"], "trialing after checkout: %r" % c)
    check(S.subscription_confirm("cs_test_s1")["ok"] and len(T.subscriptions.search()) == 1, "idempotent")
    check(S.active(boss) and S.seats_ok(boss, 8) and not S.seats_ok(boss, 9), "plan seats")
    check(S.subscription_checkout()["ok"] is False, "no second plan")
    check(S.subscription_set_seats(12)["seats"] == 12 and S.seats_ok(boss, 12), "seat change")
    check(S.subscription_portal()["url"].startswith("https://billing.stripe.com"), "portal")

    # webhook: cancelled in Stripe -> locked
    anvil.secrets.SECRETS["stripe_webhook_secret"] = "whsec_s"
    body = json.dumps({"type": "customer.subscription.deleted", "data": {"object": sub_obj("sub_1", "canceled")}}).encode()
    t = int(time.time())
    sig = "t=%d,v1=%s" % (t, hmac.new(b"whsec_s", str(t).encode() + b"." + body, hashlib.sha256).hexdigest())
    check(S.verify(body, sig, "whsec_s") and not S.verify(body, sig, "other"), "signature")
    check(S.handle_event(json.loads(body)) == "canceled" and not S.active(boss), "cancel locks")

    # expired period re-checked lazily
    T.subscriptions.delete_all_rows()
    FAKE["subs"].clear()
    S.subscription_confirm("cs_test_s1")
    row = T.subscriptions.search()[0]
    row["period_end"] = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)
    FAKE["subs"]["sub_1"]["status"] = "past_due"
    check(S.active(boss) and row["status"] == "past_due", "past_due still active (Stripe retries)")
    FAKE["subs"]["sub_1"]["status"] = "unpaid"
    row["period_end"] = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)
    check(not S.active(boss), "unpaid locks")

    # admin
    as_user(admin)
    d = S.admin_subscriptions()
    json.dumps(d)
    g = S.admin_subscription_grant("boss@example.com")
    check(g["ok"] and S.active(boss) and S.seats_ok(boss, 999), "granted plan")
    check(S.admin_subscription_action(g["row"]["id"], "revoke")["ok"] and not S.active(boss), "revoke")
    S.admin_subscription_settings({"off": True})
    check(S.active(boss) and not S.gate_on(), "off switch")
    as_user(boss)
    try:
        S.admin_subscriptions()
        check(False, "non-admin refused")
    except anvil.server.PermissionDenied:
        pass
    print("subscriptions: ALL OK")


if __name__ == "__main__":
    main()
