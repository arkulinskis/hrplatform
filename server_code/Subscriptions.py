"""Monthly plans for business apps (APP_MAKER money round 2, 2026-11-27): trial, then monthly or yearly, per seat if
the app wants it. SAME FILE IN EVERY APP (template-forms, copied by tools/payments_rollout.py); what differs per app
lives in subscriptions_config.py.

Switching on
    OFF (everything free, no prices) until the App Secret `stripe_secret_key` holds a Stripe key (sk_/rk_).
    Admin -> Plans has a switch to keep the app free even with the key in place.

Paying
    subscription_checkout() opens Stripe Checkout (mode=subscription) with a free trial (TRIAL_DAYS). The card is saved
    but only charged when the trial ends: the trial is the review window (cancel a suspicious one in Admin -> Plans).
    Back in the app (#plan/<session id>) subscription_confirm() records it, so the webhook is optional.
    subscription_portal() opens Stripe's customer portal (change card, cancel, invoices). Turn the portal on once in
    Stripe: Settings -> Billing -> Customer portal.
    Per seat (PER_SEAT = True): quantity = seats; Subscriptions.seats_ok(user, n) checks a count against the plan.

Webhook (optional, recommended): <app>/_/api/subscription/stripe, signing secret in App Secret `stripe_webhook_secret`.
    Events: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted.

Server checks elsewhere:
    from . import Subscriptions
    if not Subscriptions.active(user): return <fail with Subscriptions.LOCKED_MESSAGE>
    if not Subscriptions.seats_ok(user, employees + 1): ...
"""
import datetime as dt
import hashlib
import hmac
import json
import re
import time
import urllib.parse

import anvil.server
import anvil.users
from anvil.tables import app_tables

try:
    from . import subscriptions_config as CFG
except ImportError:
    CFG = None

API = "https://api.stripe.com/v1/"
SETTING = "subscriptions"
DEFAULTS = {"off": False}
ACTIVE = ("trialing", "active", "past_due", "granted")   # past_due: Stripe is still retrying the card
TOLERANCE = 300
LOCKED_MESSAGE = "This is part of the paid plan. Start a free trial to use it."


def cfg(name, default):
    return getattr(CFG, name, default) if CFG is not None else default


def now():
    return dt.datetime.now(dt.timezone.utc)


def _aware(v):
    return v if v is None or v.tzinfo else v.replace(tzinfo=dt.timezone.utc)


def _iso(v):
    return _aware(v).isoformat() if isinstance(v, dt.datetime) else v


def _text(v, limit=200):
    return re.sub(r"\s+", " ", "" if v is None else str(v)).strip()[:limit]


def _fail(message):
    return {"ok": False, "error": message}


def _ok(**d):
    d["ok"] = True
    return d


def _is_admin(user):
    try:
        return bool(user is not None and user["is_admin"])
    except Exception:
        return False


def _require_user():
    u = anvil.users.get_user()
    if u is None:
        raise anvil.server.PermissionDenied("Please sign in first.")
    return u


def _require_admin():
    u = _require_user()
    if not _is_admin(u):
        raise anvil.server.PermissionDenied("Only admins can do that.")
    return u


def _get_setting():
    row = app_tables.app_settings.get(key=SETTING)
    s = dict(DEFAULTS)
    if row is not None and isinstance(row["value"], dict):
        s.update({k: v for k, v in row["value"].items() if k in DEFAULTS})
    return s


def _set_setting(value):
    row = app_tables.app_settings.get(key=SETTING)
    if row is None:
        app_tables.app_settings.add_row(key=SETTING, value=value)
    else:
        row["value"] = value


def _secret(name):
    try:
        import anvil.secrets
        return str(anvil.secrets.get_secret(name) or "").strip()
    except Exception:
        return ""


def stripe_key():
    k = _secret("stripe_secret_key")
    return k if re.match(r"^(sk|rk)_(live|test)_\w+", k) else ""


def gate_on():
    return bool(stripe_key()) and not _get_setting()["off"]


def _stripe(path, fields=None, method="POST"):
    import anvil.http
    body = urllib.parse.urlencode([(k, v) for k, v in (fields or []) if v not in ("", None)])
    url = API + path + ("?" + body if method == "GET" and body else "")
    return anvil.http.request(url, method=method, data=None if method == "GET" else body, json=True,
                              headers={"Authorization": "Bearer " + stripe_key(),
                                       "Content-Type": "application/x-www-form-urlencoded"})


def user_ref(user):
    return re.sub(r"[^0-9]+", "_", user.get_id()).strip("_")


def user_from_ref(ref):
    m = re.fullmatch(r"(\d+)_(\d+)", ref or "")
    if not m:
        return None
    try:
        return app_tables.users.get_by_id("[%s,%s]" % m.groups())
    except Exception:
        return None


# ------------------------------------------------------------------------------------------------ who has a plan
def plan_of(user):
    if user is None:
        return None
    rows = sorted(app_tables.subscriptions.search(user=user), key=lambda r: r["updated"] or now(), reverse=True)
    for r in rows:
        if r["status"] in ACTIVE:
            return _fresh(r)
    return rows[0] if rows else None


def _fresh(row):
    """Re-check with Stripe once the paid period has ended (catches renewals/cancellations without the webhook)."""
    end = _aware(row["period_end"])
    if row["status"] != "granted" and row["subscription"] and end and now() > end + dt.timedelta(hours=12):
        _sync(row)
    return row


def active(user=None):
    """May this person (or their workspace owner, see owner_of in the config) use the paid features?"""
    if not gate_on():
        return True
    user = user if user is not None else anvil.users.get_user()
    if user is None:
        return False
    if _is_admin(user):
        return True
    owner = cfg("owner_of", None)
    payer = owner(user) if callable(owner) else user
    p = plan_of(payer) if payer is not None else None
    return p is not None and p["status"] in ACTIVE


def seats_ok(user, n):
    """Is n seats (people, employees) allowed? FREE_SEATS are always allowed; above that, the plan's seat count."""
    if not gate_on() or n <= cfg("FREE_SEATS", 0):
        return True
    if user is not None and _is_admin(user):
        return True
    owner = cfg("owner_of", None)
    payer = owner(user) if callable(owner) and user is not None else user
    p = plan_of(payer) if payer is not None else None
    if p is None or p["status"] not in ACTIVE:
        return False
    return p["status"] == "granted" or not cfg("PER_SEAT", False) or n <= (p["seats"] or 0)


@anvil.server.callable
def subscription_status():
    user = anvil.users.get_user()
    on = gate_on()
    p = plan_of(user) if on else None
    has = active(user)
    if not on:
        state = "free"
    elif user is None:
        state = "signed_out"
    elif p is not None and p["status"] in ACTIVE:
        state = p["status"]
    elif has:
        state = "active"   # an admin, or a member of a paying workspace
    else:
        state = "none"
    return {"gate": on, "active": has, "state": state, "name": cfg("APP_NAME", "this app"),
            "plan": cfg("PLAN_NAME", "Pro"), "price": cfg("PRICE", 29), "yearly": cfg("YEARLY", None),
            "currency": "USD", "trial_days": cfg("TRIAL_DAYS", 14), "per_seat": cfg("PER_SEAT", False),
            "free_seats": cfg("FREE_SEATS", 0), "min_seats": cfg("MIN_SEATS", 1), "seats": p["seats"] if p else None,
            "paid": list(cfg("PAID", [])), "free": list(cfg("FREE", [])), "test_mode": on and "_test_" in stripe_key(),
            "period_end": _iso(p["period_end"]) if p else None, "can_manage": bool(p is not None and p["customer"]),
            "admin": _is_admin(user)}


# ------------------------------------------------------------------------------------------------ checkout
@anvil.server.callable(require_user=True)
def subscription_checkout(interval="month", seats=None):
    me = _require_user()
    if not gate_on():
        return _fail("Everything is free right now, so there is nothing to buy.")
    p = plan_of(me)
    if p is not None and p["status"] in ACTIVE:
        return _fail("You already have a plan. Use Manage plan to change it.")
    yearly = cfg("YEARLY", None)
    interval = "year" if interval == "year" and yearly else "month"
    price = yearly if interval == "year" else cfg("PRICE", 29)
    qty = 1
    if cfg("PER_SEAT", False):
        try:
            qty = max(int(seats or 0), int(cfg("MIN_SEATS", 1)))
        except (TypeError, ValueError):
            qty = int(cfg("MIN_SEATS", 1))
    origin = (anvil.server.get_app_origin() or "").rstrip("/")
    name = "%s %s" % (cfg("APP_NAME", "App"), cfg("PLAN_NAME", "Pro"))
    fields = [("mode", "subscription"),
              ("success_url", origin + "/#plan/{CHECKOUT_SESSION_ID}"),
              ("cancel_url", origin + "/#plan-cancelled"),
              ("client_reference_id", user_ref(me)),
              ("customer_email", me["email"] or ""),
              ("line_items[0][quantity]", str(qty)),
              ("line_items[0][price_data][currency]", "usd"),
              ("line_items[0][price_data][unit_amount]", str(int(round(float(price) * 100)))),
              ("line_items[0][price_data][recurring][interval]", interval),
              ("line_items[0][price_data][product_data][name]", name + (" (per seat)" if cfg("PER_SEAT", False) else "")),
              ("metadata[sub]", "1"),
              ("subscription_data[metadata][sub]", "1"),
              ("subscription_data[metadata][user]", user_ref(me)),
              ("allow_promotion_codes", "true")]
    if int(cfg("TRIAL_DAYS", 14) or 0) > 0:
        fields.append(("subscription_data[trial_period_days]", str(int(cfg("TRIAL_DAYS", 14)))))
    try:
        r = _stripe("checkout/sessions", fields)
    except Exception as e:
        print("Subscription checkout failed: %r" % (e,))
        return _fail("We couldn't reach the payment page. Please try again in a minute.")
    url = str(r.get("url") or "") if isinstance(r, dict) else ""
    return _ok(url=url) if url.startswith("https://") else _fail("We couldn't reach the payment page.")


def _apply(row, sub):
    """Copy a Stripe subscription object onto a row."""
    items = ((sub.get("items") or {}).get("data") or [{}])
    it = items[0] if items else {}
    end = sub.get("current_period_end") or it.get("current_period_end")
    row.update(status=_text(sub.get("status"), 30) or row["status"], subscription=_text(sub.get("id"), 120),
               customer=_text(sub.get("customer"), 120) or row["customer"], item=_text(it.get("id"), 120) or row["item"],
               seats=int(it.get("quantity") or row["seats"] or 1),
               interval=_text(((it.get("price") or {}).get("recurring") or {}).get("interval"), 10) or row["interval"],
               period_end=dt.datetime.fromtimestamp(int(end), dt.timezone.utc) if end else row["period_end"],
               updated=now())
    return row


def _record(session, sub):
    sid = _text(session.get("id"), 120)
    if not sid or session.get("status") != "complete" or not isinstance(sub, dict):
        return None
    row = app_tables.subscriptions.get(subscription=_text(sub.get("id"), 120))
    if row is None:
        user = user_from_ref(_text(session.get("client_reference_id"), 80))
        email = _text(((session.get("customer_details") or {}).get("email")) or session.get("customer_email")).lower()
        if user is None and email:
            user = app_tables.users.get(email=email)
        row = app_tables.subscriptions.add_row(user=user, email=email, status="incomplete", subscription=None,
                                               customer=None, item=None, seats=1, interval="month", period_end=None,
                                               created=now(), updated=now(), note=None)
    return _apply(row, sub)


@anvil.server.callable
def subscription_confirm(session_id):
    sid = _text(session_id, 120)
    if not re.fullmatch(r"cs_(live|test)_\w+", sid) or not stripe_key():
        return _fail("That payment link isn't valid.")
    try:
        session = _stripe("checkout/sessions/" + sid, [("expand[]", "subscription")], method="GET")
    except Exception as e:
        print("Subscription confirm failed: %r" % (e,))
        return _fail("We couldn't check the payment yet. Refresh in a minute.")
    row = _record(session, session.get("subscription"))
    if row is None:
        return _fail("Stripe hasn't confirmed this plan yet. It will show up soon.")
    return _ok(status=row["status"], active=row["status"] in ACTIVE)


def _sync(row):
    if not row["subscription"] or not stripe_key():
        return row
    try:
        return _apply(row, _stripe("subscriptions/" + row["subscription"], method="GET"))
    except Exception as e:
        print("Subscription sync failed: %r" % (e,))
        return row


@anvil.server.callable(require_user=True)
def subscription_portal():
    me = _require_user()
    p = plan_of(me)
    if p is None or not p["customer"]:
        return _fail("There is no plan to manage yet.")
    try:
        r = _stripe("billing_portal/sessions", [("customer", p["customer"]),
                                                ("return_url", (anvil.server.get_app_origin() or "").rstrip("/") + "/#plan-back")])
    except Exception as e:
        print("Portal failed: %r" % (e,))
        return _fail("Stripe's plan page isn't set up yet (Stripe: Settings, Billing, Customer portal).")
    return _ok(url=r.get("url"))


@anvil.server.callable(require_user=True)
def subscription_set_seats(n):
    """Change the seat count (per-seat plans): prorated by Stripe."""
    me = _require_user()
    p = plan_of(me)
    if not cfg("PER_SEAT", False) or p is None or p["status"] not in ("trialing", "active") or not p["item"]:
        return _fail("There is no seat plan to change.")
    try:
        n = max(int(n), int(cfg("MIN_SEATS", 1)))
        sub = _stripe("subscriptions/" + p["subscription"], [("items[0][id]", p["item"]), ("items[0][quantity]", str(n)),
                                                             ("proration_behavior", "create_prorations")])
    except Exception as e:
        print("Seat change failed: %r" % (e,))
        return _fail("Stripe didn't accept the change. Try again in a minute.")
    _apply(p, sub)
    return _ok(seats=p["seats"])


# ------------------------------------------------------------------------------------------------ webhook
def verify(raw, header, secret, at=None):
    if not header or not secret:
        return False
    parts = {}
    for kv in str(header).split(","):
        k, _, v = kv.strip().partition("=")
        parts.setdefault(k, []).append(v)
    try:
        t = int((parts.get("t") or ["0"])[0])
    except ValueError:
        return False
    if abs((at or time.time()) - t) > TOLERANCE:
        return False
    expected = hmac.new(secret.encode("utf-8"), str(t).encode("utf-8") + b"." + raw, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, v) for v in parts.get("v1", []))


def handle_event(event):
    kind = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}
    if kind == "checkout.session.completed":
        if (obj.get("metadata") or {}).get("sub") != "1" or not obj.get("subscription"):
            return "not ours"
        try:
            sub = _stripe("subscriptions/" + str(obj["subscription"]), method="GET")
        except Exception:
            return "waiting"
        return "recorded" if _record(obj, sub) is not None else "waiting"
    if kind in ("customer.subscription.updated", "customer.subscription.deleted"):
        row = app_tables.subscriptions.get(subscription=_text(obj.get("id"), 120))
        if row is None:
            return "unknown"
        _apply(row, obj)
        if kind.endswith("deleted"):
            row.update(status="canceled", updated=now())
        return row["status"]
    return "ignored"


@anvil.server.http_endpoint("/subscription/stripe", methods=["POST"])
def subscription_webhook(**kw):
    b = anvil.server.request.body
    if b is None:
        raw = b""
    elif hasattr(b, "get_bytes"):
        raw = getattr(b, "get_bytes")()
    else:
        raw = b.encode("utf-8") if isinstance(b, str) else bytes(b)
    headers = {str(k).lower(): v for k, v in (anvil.server.request.headers or {}).items()}
    secret = _secret("stripe_webhook_secret")

    def reply(status, data):
        return anvil.server.HttpResponse(status, json.dumps(data), headers={"Content-Type": "application/json"})
    if not secret:
        return reply(503, {"error": "stripe_webhook_secret isn't set in App Secrets"})
    if not verify(raw, headers.get("stripe-signature"), secret):
        return reply(400, {"error": "bad signature"})
    try:
        event = json.loads(raw.decode("utf-8"))
    except ValueError:
        return reply(400, {"error": "bad json"})
    return reply(200, {"received": True, "result": handle_event(event)})


# ------------------------------------------------------------------------------------------------ admin
def _row(r):
    return {"id": r.get_id(), "email": r["email"] or (r["user"]["email"] if r["user"] else ""), "status": r["status"],
            "seats": r["seats"] or 1, "interval": r["interval"] or "", "period_end": _iso(r["period_end"]),
            "created": _iso(r["created"]), "note": r["note"] or "", "stripe": bool(r["subscription"])}


@anvil.server.callable(require_user=True)
def admin_subscriptions():
    _require_admin()
    rows = sorted(app_tables.subscriptions.search(), key=lambda r: r["created"] or now(), reverse=True)
    s = _get_setting()
    return {"settings": s, "key_set": bool(stripe_key()), "test_mode": "_test_" in stripe_key(), "gate": gate_on(),
            "webhook_set": bool(_secret("stripe_webhook_secret")),
            "webhook_url": (anvil.server.get_app_origin() or "").rstrip("/") + "/_/api/subscription/stripe",
            "rows": [_row(r) for r in rows[:300]],
            "counts": {k: len([r for r in rows if r["status"] == k]) for k in
                       ("trialing", "active", "past_due", "canceled", "granted")}}


@anvil.server.callable(require_user=True)
def admin_subscription_settings(changes):
    _require_admin()
    s = _get_setting()
    if "off" in (changes or {}):
        s["off"] = bool(changes["off"])
    _set_setting(s)
    return _ok(settings=s, gate=gate_on())


@anvil.server.callable(require_user=True)
def admin_subscription_action(row_id, action):
    """sync | cancel (ends a trial or plan in Stripe now) | revoke (a free plan you gave)."""
    _require_admin()
    try:
        r = app_tables.subscriptions.get_by_id(row_id)
    except Exception:
        r = None
    if r is None:
        return _fail("That plan is gone.")
    try:
        if action == "sync":
            _sync(r)
        elif action == "cancel":
            if not r["subscription"] or r["status"] not in ("trialing", "active", "past_due"):
                return _fail("Only a running Stripe plan can be cancelled here.")
            _apply(r, _stripe("subscriptions/" + r["subscription"], method="DELETE"))
            r.update(status="canceled", updated=now())
        elif action == "revoke":
            if r["status"] != "granted":
                return _fail("Only a free plan you gave can be taken back.")
            r.update(status="revoked", updated=now())
        else:
            return _fail("Unknown action.")
    except Exception as e:
        print("Subscription %s failed: %r" % (action, e))
        return _fail("Stripe said no: %s" % (getattr(e, "content", None) or e,))
    return _ok(row=_row(r))


@anvil.server.callable(require_user=True)
def admin_subscription_grant(email, note=""):
    _require_admin()
    email = _text(email).lower()
    user = app_tables.users.get(email=email) if "@" in email else None
    if user is None:
        return _fail("Nobody with that email has an account yet.")
    r = app_tables.subscriptions.add_row(user=user, email=email, status="granted", subscription=None, customer=None,
                                         item=None, seats=9999, interval="", period_end=None, created=now(),
                                         updated=now(), note=_text(note, 300) or "Given by admin")
    return _ok(row=_row(r))
