import anvil.server
from anvil import *

from ._anvil_designer import PlanAdminTemplate
from ... import state, subscription

WORDS = {"trialing": "free trial", "active": "paying", "past_due": "payment failed (Stripe retrying)",
         "canceled": "cancelled", "granted": "free (given)", "revoked": "taken back", "incomplete": "not finished",
         "unpaid": "unpaid"}


class PlanAdmin(PlanAdminTemplate):
    """Admin: is the plan gate on, the off switch, every plan (Cancel a suspicious trial before it charges, Check
    Stripe), and free plans by email. Open from the Admin page:
    alert(PlanAdmin(), buttons=[], role="app-dialog", large=True)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self._armed = None
        self.load()

    def load(self):
        d = state.call("admin_subscriptions")
        if not d:
            return
        if not d["key_set"]:
            self.gate_label.text = "Gate off: everything is free. Add the App Secret stripe_secret_key to switch it on."
        elif d["settings"]["off"]:
            self.gate_label.text = "Gate off by your switch: everything is free."
        else:
            self.gate_label.text = "Gate ON%s: paid features need a plan." % (" (Stripe TEST mode)" if d["test_mode"] else "")
        self.setup_label.text = "Webhook: %s. Stripe -> Developers -> Webhooks -> %s" % (
            "set" if d["webhook_set"] else "not set (optional; App Secret stripe_webhook_secret)", d["webhook_url"])
        self.off_box.checked = bool(d["settings"]["off"])
        c = d["counts"]
        self.counts_label.text = "%d on trial, %d paying, %d payment failed, %d cancelled, %d free." % (
            c["trialing"], c["active"], c["past_due"], c["canceled"], c["granted"])
        self.rows_panel.clear()
        for r in d["rows"]:
            self.rows_panel.add_component(self._row(r))
        self.empty_label.visible = not d["rows"]

    def _row(self, r):
        line = FlowPanel()
        bits = [r["email"] or "(no email)", WORDS.get(r["status"], r["status"])]
        if r["seats"] and r["seats"] < 9999:
            bits.append("%d seat%s" % (r["seats"], "" if r["seats"] == 1 else "s"))
        if r["period_end"]:
            bits.append(("trial ends " if r["status"] == "trialing" else "renews ") + r["period_end"][:10])
        if r["note"]:
            bits.append(r["note"])
        line.add_component(Label(text="  ·  ".join(bits), bold=r["status"] in ("trialing", "past_due")))
        acts = []
        if r["status"] in ("trialing", "active", "past_due") and r["stripe"]:
            acts.append(("Cancel", "cancel", "btn-danger"))
        if r["status"] == "granted":
            acts.append(("Take back", "revoke", "btn-ghost"))
        if r["stripe"]:
            acts.append(("Check Stripe", "sync", "btn-ghost"))
        for text, action, role in acts:
            b = Button(text=text, role=["btn", role])
            b.add_event_handler("click", lambda a=action, rid=r["id"], btn=b, **e: self.act(rid, a, btn))
            line.add_component(b)
        return line

    def act(self, row_id, action, button=None):
        if action == "cancel" and self._armed != row_id:
            self._armed = row_id   # second click confirms (no pop-up on top of this dialog)
            if button is not None:
                button.text = "Sure? Click again (ends the plan in Stripe now)"
            return
        self._armed = None
        if state.call("admin_subscription_action", row_id, action):
            state.toast({"cancel": "Plan cancelled.", "revoke": "Free plan taken back.", "sync": "Checked with Stripe."}[action], "ok")
        subscription.reset()
        self.load()

    @handle("off_box", "change")
    def off_box_change(self, **event_args):
        state.call("admin_subscription_settings", {"off": self.off_box.checked})
        subscription.reset()
        self.load()

    @handle("grant_button", "click")
    def grant_button_click(self, **event_args):
        r = anvil.server.call("admin_subscription_grant", self.grant_box.text or "")
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error"), True
            return
        self.message.visible, self.grant_box.text = False, ""
        state.toast("Free plan given.", "ok")
        self.load()

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
