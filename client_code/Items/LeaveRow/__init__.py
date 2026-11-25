from anvil import *

from ._anvil_designer import LeaveRowTemplate
from ... import router, state


class LeaveRow(LeaveRowTemplate):
    """One time-off request (Leave._req dict) plus item["show_person"] (False on my own list).
    Buttons raise events on the panel: x-decide(req, approve, button) and x-cancel(req, button)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        show = bool(it.get("show_person"))
        self.av_box.visible = show
        self.person_link.visible = show
        if show and it.get("person_id"):
            state.set_attr(self.person_link, "href", router.href("person", it["person_id"]))
        self.dot.classes["lv-" + (it.get("color") or "slate")] = True
        state.badge(self.status, it.get("status") or "pending")
        self.when.text = "%s · %s" % (state.date_range(it.get("start"), it.get("end")), state.days(it.get("days")))
        if it.get("note"):
            self.note.text, self.note.visible = "“%s”" % it["note"], True
        bits = []
        if it.get("decided_by") and it.get("status") in ("approved", "declined", "cancelled"):
            verb = {"approved": "Approved", "declined": "Declined", "cancelled": "Cancelled"}[it["status"]]
            bits.append("%s by %s" % (verb, it["decided_by"]))
        if it.get("decision_note"):
            bits.append("“%s”" % it["decision_note"])
        if bits:
            self.decision.text, self.decision.visible = " · ".join(bits), True
        self.approve_button.visible = bool(it.get("can_decide"))
        self.decline_button.visible = bool(it.get("can_decide"))
        self.cancel_button.visible = bool(it.get("can_cancel"))
        self.actions.visible = bool(it.get("can_decide") or it.get("can_cancel"))
        state.set_attr(self.row, "data-req", it.get("id") or "")
        if show:
            who = it.get("person") or "this person"
            state.set_control_attr(self.approve_button, "aria-label", "Approve %s's request" % who)
            state.set_control_attr(self.decline_button, "aria-label", "Decline %s's request" % who)

    @handle("approve_button", "click")
    def approve_button_click(self, **event_args):
        self.parent.raise_event("x-decide", req=self.item, approve=True, button=self.approve_button)

    @handle("decline_button", "click")
    def decline_button_click(self, **event_args):
        self.parent.raise_event("x-decide", req=self.item, approve=False, button=self.decline_button)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.parent.raise_event("x-cancel", req=self.item, button=self.cancel_button)
