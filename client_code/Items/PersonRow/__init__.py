from anvil import *

from ._anvil_designer import PersonRowTemplate
from ... import router, state


class PersonRow(PersonRowTemplate):
    """A compact person line: {id or href, name, sub, initials, tone, tag?, tag_role?}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        state.set_attr(self.link, "href", it.get("href") or router.href("person", it.get("id") or ""))
        if it.get("tag"):
            self.tag_label.text, self.tag_label.visible = it["tag"], True
            if it.get("tag_role"):
                self.tag_label.role = ["badge", it["tag_role"]]
