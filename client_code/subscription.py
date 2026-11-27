"""Monthly plans on the page side (server: Subscriptions.py; same file in every app).

    subscription.status(refresh=False)  the server's subscription_status() (cached per signed-in person)
    subscription.active()               True when the paid features may be used (always True while the gate is off)
    subscription.gate_on()              True once a Stripe key is set (show prices / plan links only then)
    subscription.gate("Reports")        True if active; otherwise shows the plan offer and returns False
    subscription.offer(feature=None)    shows the plan dialog (start trial, or manage the plan)
    subscription.seats_ok(n)            page-side seat check (the server checks too)
    subscription.handle_return()        call once at start-up, before router.start()
"""
import anvil.server
from anvil.js import window

from . import state

_s: dict = {"status": None, "who": None}


def _who():
    try:
        m = state.me()
        return ((m or {}).get("id") or (m or {}).get("email")) if m else None
    except Exception:
        return None


def status(refresh=False):
    who = _who()
    if refresh or _s["status"] is None or who != _s["who"]:
        _s["who"] = who
        try:
            _s["status"] = anvil.server.call("subscription_status")
        except Exception as e:
            print("subscription_status failed: %r" % (e,))
            _s["status"] = {"gate": False, "active": True, "state": "free", "paid": [], "free": []}
    return _s["status"]


def reset():
    _s["status"] = None


def active():
    return bool(status().get("active"))


def gate_on():
    return bool(status().get("gate"))


def seats_ok(n):
    s = status()
    if not s.get("gate") or n <= (s.get("free_seats") or 0):
        return True
    if not s.get("active"):
        return False
    return not s.get("per_seat") or s.get("state") == "granted" or s.get("seats") is None or n <= s["seats"]


def offer(feature=None):
    from anvil import alert
    from .Dialogs.PlanOffer import PlanOffer
    alert(PlanOffer(feature=feature), buttons=[], role="app-dialog")


def gate(feature=None):
    if active():
        return True
    offer(feature)
    return False


def handle_return():
    h = str(window.location.hash or "")
    if h.startswith("#plan/"):
        r = anvil.server.call("subscription_confirm", h[len("#plan/"):].split("?")[0])
        if r.get("ok"):
            state.toast("Your plan is on. Thank you!" if r.get("status") == "active" else
                        "Your free trial has started. Your card is charged when it ends; cancel any time.", "ok")
        else:
            state.toast(r.get("error") or "We couldn't check the plan yet.", "error")
        window.history.replaceState(None, "", "#")
        status(refresh=True)
    elif h.startswith("#plan-cancelled"):
        state.toast("No plan was started.")
        window.history.replaceState(None, "", "#")
    elif h.startswith("#plan-back"):
        window.history.replaceState(None, "", "#")
        status(refresh=True)
