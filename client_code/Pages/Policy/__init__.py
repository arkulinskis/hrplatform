import anvil.server
from anvil import *

from ._anvil_designer import PolicyTemplate
from ... import router, state


def _tone(text):
    return sum(ord(ch) for ch in (text or "")) % 6


class Policy(PolicyTemplate):
    """#policy/<id>: the policy text in a comfortable reading column, "I have read and understood this"
    (then the date you acknowledged it). HR: Edit, Delete and who has / hasn't acknowledged it."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._id = args[0] if args else None
        self._p: dict = {}
        state.heading(self.title_label, 1)
        self._load()

    def _load(self):
        r: dict = {"ok": False}
        if self._id:
            r = anvil.server.call("get_policy", self._id)
        ok = bool(r.get("ok"))
        self.missing_box.visible = not ok
        self.main_box.visible = ok
        if not ok:
            self.missing_text.text = r.get("error") or "It may have been deleted."
            return
        p = r["policy"]
        self._p = p
        hr = state.is_hr()
        self.title_label.text = p["title"]
        words = p.get("words") or 0
        bits = ["about %d min read" % max(1, int(round(words / 220.0)))]
        if p.get("updated"):
            bits.insert(0, "Updated " + state.fmt_date(p["updated"]))
        self.meta.text = " · ".join(bits)
        self.body.text = p.get("body") or ""
        self.hr_actions.visible = hr
        need = bool(p.get("require_ack"))
        acked = bool(p.get("acked"))
        self.ack_box.visible = need and not acked
        self.acked_badge.visible = need and acked
        if need and acked:
            when = p.get("acked_at")
            self.acked_badge.text = ("You acknowledged this on %s" % state.fmt_date(when)) if when else \
                "You have acknowledged this"
        self.ref_note.visible = not need
        status = p.get("status")
        self.who_box.visible = bool(hr and need and status is not None)
        if hr and need and status is not None:
            def row(x):
                return {"id": x["id"], "name": x["name"], "initials": state.initials(x["name"]),
                        "tone": _tone(x["name"]), "sub": ""}
            yes = [row(x) for x in status if x["acked"]]
            no = [row(x) for x in status if not x["acked"]]
            self.yes_head.text = "Acknowledged (%d)" % len(yes)
            self.no_head.text = "Not yet (%d)" % len(no)
            self.who_summary.text = "%d of %d people acknowledged the current version." % (len(yes), len(status))
            self.yes_panel.items = yes
            self.no_panel.items = no
            self.no_yes.visible = not yes
            self.no_no.visible = not no

    @handle("ack_button", "click")
    def ack_button_click(self, **event_args):
        self.ack_button.enabled = False
        self.ack_button.role = ["btn", "btn-primary", "btn-lg", "ic-check", "btn-is-busy"]
        try:
            r = state.call("acknowledge", self._id)
        finally:
            self.ack_button.enabled = True
            self.ack_button.role = ["btn", "btn-primary", "btn-lg", "ic-check"]
        if r is not None:
            state.toast("Thanks, your acknowledgement is recorded", "ok")
            self._load()

    @handle("edit_button", "click")
    def edit_button_click(self, **event_args):
        from ...Dialogs.PolicyEdit import PolicyEdit
        if alert(PolicyEdit(policy=self._p), buttons=[], role="app-dialog", large=True):
            state.toast("Policy saved", "ok")
            self._load()

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if not confirm("The policy and everyone's acknowledgements of it are deleted. This can't be undone.",
                       title="Delete \"%s\"?" % self._p.get("title", "this policy"),
                       buttons=[("Cancel", False), ("Delete policy", True)], role="app-dialog"):
            return
        if state.call("delete_policy", self._id) is not None:
            state.toast("Policy deleted", "ok")
            router.go("docs")
