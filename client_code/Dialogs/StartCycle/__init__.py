import datetime

import anvil.server
from anvil import *

from ._anvil_designer import StartCycleTemplate
from ... import state


class StartCycle(StartCycleTemplate):
    """HR starts a review cycle: name, due date and the questions (one per line). Closes with the server reply
    ({cycle, reviews}) or None."""

    def __init__(self, questions=(), **properties):
        super().__init__(**properties)
        state.set_control_attr(self.due_box, "type", "date")
        today = datetime.date.today()
        self.due_box.text = (today + datetime.timedelta(days=21)).isoformat()
        season = ["Winter", "Winter", "Spring", "Spring", "Spring", "Summer", "Summer", "Summer", "Autumn", "Autumn",
                  "Autumn", "Winter"][today.month - 1]
        self.name_box.text = "%s %d reviews" % (season, today.year)
        self.questions_box.text = "\n".join(questions or [])

    @handle("", "show")
    def form_show(self, **event_args):
        self.name_box.focus()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    def _error(self, text):
        self.message.text, self.message.visible = text, True

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        if len(name) < 3:
            self._error("Name the cycle, for example Spring 2027 reviews.")
            return
        qs = [line.strip() for line in (self.questions_box.text or "").split("\n") if line.strip()]
        if not qs:
            self._error("Add at least one question.")
            return
        if len(qs) > 8:
            self._error("Keep it to 8 questions or fewer: shorter reviews get better answers.")
            return
        self.save_button.enabled = False
        self.save_button.role = ["btn", "btn-primary", "ic-check", "btn-is-busy"]
        try:
            r = anvil.server.call("start_cycle", name, self.due_box.text or None, qs)
        finally:
            self.save_button.enabled = True
            self.save_button.role = ["btn", "btn-primary", "ic-check"]
        if not r.get("ok"):
            self._error(r.get("error") or "That didn't work.")
            return
        self.raise_event("x-close-alert", value=r)
