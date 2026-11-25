import anvil.server
from anvil import *

from ._anvil_designer import AnnounceTemplate


class Announce(AnnounceTemplate):
    """HR posts an announcement (title, message, pinned). Closes with the new announcement or None."""

    def __init__(self, **properties):
        super().__init__(**properties)

    @handle("", "show")
    def form_show(self, **event_args):
        self.title_box.focus()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        title = (self.title_box.text or "").strip()
        if len(title) < 3:
            self.message.text, self.message.visible = "Give the announcement a title.", True
            return
        self.save_button.enabled = False
        self.save_button.role = ["btn", "btn-primary", "ic-megaphone", "btn-is-busy"]
        try:
            r = anvil.server.call("post_announcement", title, self.body_box.text or "", bool(self.pinned_box.checked))
        finally:
            self.save_button.enabled = True
            self.save_button.role = ["btn", "btn-primary", "ic-megaphone"]
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=r["announcement"])
