from anvil import *
from anvil.js import window

from ._anvil_designer import InviteTemplate


class Invite(InviteTemplate):
    """Shows the one-time invite link for someone's profile, with Copy."""

    def __init__(self, name, code, **properties):
        super().__init__(**properties)
        self.heading.text = "Invite %s" % name
        self.link_box.text = "%s%s#join/%s" % (window.location.origin, window.location.pathname, code)

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        window.HR.copy(self.link_box.text)
        self.copied.visible = True

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
