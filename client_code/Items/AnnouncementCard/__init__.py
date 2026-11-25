from anvil import *

from ._anvil_designer import AnnouncementCardTemplate
from ... import router, state


class AnnouncementCard(AnnouncementCardTemplate):
    """An announcement: {id, title, body, author, author_initials, author_tone, pinned, created, can_delete?}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.meta.text = "%s · %s" % (it["author"] or "HR", state.ago(it["created"]))
        self.delete_button.visible = bool(it.get("can_delete"))

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if confirm("Everyone will stop seeing it.", title="Delete this announcement?",
                   buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            if state.call("delete_announcement", self.item["id"]) is not None:
                self.parent.raise_event("x-changed")
