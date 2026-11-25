import anvil.server
from anvil import *

from ._anvil_designer import PolicyEditTemplate


class PolicyEdit(PolicyEditTemplate):
    """HR writes or edits a policy: title, text, needs acknowledgement. policy = the full policy dict (None = new).
    Closes with the saved policy or None."""

    def __init__(self, policy=None, **properties):
        super().__init__(**properties)
        self._policy: dict = dict(policy or {})
        p = self._policy
        if p.get("id"):
            self.heading.text = "Edit policy"
            self.title_box.text = p.get("title", "")
            self.body_box.text = p.get("body", "")
            self.ack_box.checked = bool(p.get("require_ack"))
        self.note.visible = bool(p.get("id")) and bool(self.ack_box.checked)

    @handle("", "show")
    def form_show(self, **event_args):
        self.title_box.focus()

    @handle("ack_box", "change")
    def ack_box_change(self, **event_args):
        self.note.visible = bool(self._policy.get("id")) and bool(self.ack_box.checked)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        title, body = (self.title_box.text or "").strip(), (self.body_box.text or "").strip()
        if len(title) < 3 or len(body) < 10:
            self.message.text, self.message.visible = "A policy needs a title and some text.", True
            return
        self.save_button.enabled = False
        self.save_button.role = ["btn", "btn-primary", "ic-check", "btn-is-busy"]
        try:
            r = anvil.server.call("save_policy", self._policy.get("id"), title, body, bool(self.ack_box.checked))
        finally:
            self.save_button.enabled = True
            self.save_button.role = ["btn", "btn-primary", "ic-check"]
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=r["policy"])
