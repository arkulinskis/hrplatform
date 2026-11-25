import anvil.server
from anvil import *

from ._anvil_designer import GiveKudosTemplate
from ... import state


class GiveKudos(GiveKudosTemplate):
    """Kudos for a colleague: person (people = [{id, name}]), an optional company value, a message.
    Closes with the new kudos dict or None."""

    def __init__(self, people=(), values=(), **properties):
        super().__init__(**properties)
        self.person_drop.items = [("Choose a colleague", "")] + [(p["name"], p["id"]) for p in (people or [])]
        self.person_drop.selected_value = ""
        vals = list(values or [])
        self.values_box.visible = bool(vals)
        self.value_drop.items = [("No particular value", "")] + [(v, v) for v in vals]
        self.value_drop.selected_value = ""
        state.set_control_attr(self.value_drop, "aria-label", "Company value (optional)")

    @handle("", "show")
    def form_show(self, **event_args):
        state.focus(self.person_drop)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    def _error(self, text):
        self.message.text, self.message.visible = text, True

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        who = self.person_drop.selected_value
        text = (self.message_box.text or "").strip()
        if not who:
            self._error("Choose who the kudos are for.")
            return
        if len(text) < 3:
            self._error("Say what they did.")
            return
        self.save_button.enabled = False
        self.save_button.role = ["btn", "btn-primary", "ic-award", "btn-is-busy"]
        try:
            r = anvil.server.call("give_kudos", who, self.value_drop.selected_value or "", text)
        finally:
            self.save_button.enabled = True
            self.save_button.role = ["btn", "btn-primary", "ic-award"]
        if not r.get("ok"):
            self._error(r.get("error") or "That didn't work.")
            return
        self.raise_event("x-close-alert", value=r["kudos"])
