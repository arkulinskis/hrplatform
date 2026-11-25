from anvil import *

from ._anvil_designer import PersonCardTemplate
from ... import router, state


class PersonCard(PersonCardTemplate):
    """A person in the directory. item = a card dict from list_people."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        state.set_attr(self.link, "href", router.href("person", it["id"]))
        self.meta.text = " · ".join(x for x in [it.get("department"), it.get("location")] if x)
        if it.get("status") in ("onboarding", "leave", "terminated"):
            state.badge(self.status, it["status"])
            self.status.visible = True
        if it.get("is_me"):
            self.status.text, self.status.role, self.status.visible = "You", ["badge", "badge-brand"], True
