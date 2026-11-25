import anvil.server
from anvil import *

from ._anvil_designer import TerminateTemplate
from ... import state

REASONS = ["Resignation", "End of contract", "Redundancy", "Dismissal", "Retirement", "Other"]


class Terminate(TerminateTemplate):
    """Offboard someone: last day, reason, regretted, rehire eligibility, a private note."""

    def __init__(self, person, **properties):
        super().__init__(**properties)
        self._p = person
        self.heading.text = "Offboard %s" % person["name"]
        state.set_control_attr(self.end_date, "type", "date")
        self.reason.items = REASONS

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        if not self.end_date.text:
            self.message.text, self.message.visible = "Choose their last working day.", True
            return
        self.save_button.enabled = False
        try:
            r = anvil.server.call("terminate", self._p["id"], {
                "end_date": self.end_date.text, "reason": self.reason.selected_value,
                "regretted": bool(self.regretted.checked), "rehire": bool(self.rehire.checked), "note": self.note.text or ""})
        finally:
            self.save_button.enabled = True
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=r["person"])
