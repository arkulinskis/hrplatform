import anvil.server
from anvil import *

from ._anvil_designer import DecideRequestTemplate
from ... import state


class DecideRequest(DecideRequestTemplate):
    """Decline a time-off request with an optional note. Closes with the updated request dict, or None."""

    def __init__(self, req=None, **properties):
        self._req: dict = dict(req or {})
        super().__init__(**properties)
        r = self._req
        self.summary.text = "%s asked for %s of %s (%s)." % (
            r.get("person") or "Someone", state.days(r.get("days")), (r.get("type") or "time off").lower(),
            state.date_range(r.get("start"), r.get("end")))

    @handle("", "show")
    def form_show(self, **event_args):
        self.note_box.focus()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("decline_button", "click")
    def decline_button_click(self, **event_args):
        self.decline_button.enabled = False
        try:
            r = anvil.server.call("decide_request", self._req.get("id"), False, self.note_box.text or "")
        finally:
            self.decline_button.enabled = True
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=r["request"])
