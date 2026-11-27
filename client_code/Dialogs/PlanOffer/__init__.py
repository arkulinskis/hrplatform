import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import PlanOfferTemplate
from ... import subscription


def _money(v):
    v = float(v)
    return "$%d" % v if v.is_integer() else "$%.2f" % v


class PlanOffer(PlanOfferTemplate):
    """The plan offer: monthly / yearly, seats for per-seat plans, the free trial button, and Manage plan (Stripe's
    customer portal) for people who already have one."""

    def __init__(self, feature=None, **properties):
        super().__init__(**properties)
        s = subscription.status(refresh=True)
        self.s, self.interval = s, "month"
        self.title_label.text = "%s %s" % (s.get("name", ""), s.get("plan", "Pro"))
        if feature:
            self.feature_label.text, self.feature_label.visible = "%s is part of the paid plan." % feature, True
        self.year_button.visible = bool(s.get("yearly"))
        self.month_button.visible = bool(s.get("yearly"))
        self.seats_field.visible = bool(s.get("per_seat"))
        self.seats_box.text = str(max(s.get("min_seats") or 1, (s.get("free_seats") or 0) + 1))
        self.paid_list.text = "\n".join("+ " + p for p in s.get("paid") or [])
        self.free_list.text = "\n".join("- " + p for p in s.get("free") or [])
        self.free_head.visible = self.free_list.visible = bool(s.get("free"))
        self.test_note.visible = bool(s.get("test_mode"))
        trial = s.get("trial_days") or 0
        self.buy_button.text = "Start %d-day free trial" % trial if trial else "Subscribe"
        st = s.get("state")
        if st == "signed_out":
            self.buy_button.text = "Sign in to start"
        elif st in ("trialing", "active", "past_due", "granted", "free"):
            self.buy_button.visible = False
            self.manage_button.visible = bool(s.get("can_manage"))
        self._draw()

    def _draw(self):
        s = self.s
        st = s.get("state")
        per = " per seat" if s.get("per_seat") else ""
        if self.interval == "year":
            self.price_label.text = "%s a year%s" % (_money(s.get("yearly")), per)
        else:
            self.price_label.text = "%s a month%s" % (_money(s.get("price", 0)), per)
        self.month_button.role = ["seg", "on"] if self.interval == "month" else ["seg"]
        self.year_button.role = ["seg", "on"] if self.interval == "year" else ["seg"]
        notes = {"trialing": "Your free trial is on.", "active": "Your plan is on. Thank you!",
                 "past_due": "Your last payment failed. Update your card in Manage plan.",
                 "granted": "You have the plan for free.", "free": "Everything is free right now."}
        self.price_note.text = notes.get(st) or (
            "%d days free, then charged. Cancel any time." % s.get("trial_days") if s.get("trial_days") else "Cancel any time.")

    @handle("month_button", "click")
    def month_button_click(self, **event_args):
        self.interval = "month"
        self._draw()

    @handle("year_button", "click")
    def year_button_click(self, **event_args):
        self.interval = "year"
        self._draw()

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("manage_button", "click")
    def manage_button_click(self, **event_args):
        r = anvil.server.call("subscription_portal")
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error"), True
            return
        window.location.href = r["url"]

    @handle("buy_button", "click")
    def buy_button_click(self, **event_args):
        if self.s.get("state") == "signed_out":
            self.raise_event("x-close-alert", value=None)
            window.location.hash = "#auth"
            return
        self.buy_button.enabled = False
        r = anvil.server.call("subscription_checkout", self.interval, self.seats_box.text or "")
        if not r.get("ok"):
            self.buy_button.enabled = True
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        window.location.href = r["url"]
