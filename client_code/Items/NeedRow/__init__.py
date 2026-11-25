from anvil import *

from ._anvil_designer import NeedRowTemplate
from ... import router, state


class NeedRow(NeedRowTemplate):
    """One thing that needs you (home inbox): {kind, icon, title, sub, href, overdue}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        state.set_attr(self.link, "href", it["href"])
        self.icon.classes.add("ic-" + (it.get("icon") or "check"))
        self.icon_box.classes.add("k-" + it["kind"])
        self.late.visible = bool(it.get("overdue"))
