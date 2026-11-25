from anvil import *

from ._anvil_designer import HistoryRowTemplate
from ... import router, state


class HistoryRow(HistoryRowTemplate):
    """One change in someone's record: {field, old, new, effective, by, kind, person?, show_person?}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        old, new = it.get("old") or "", it.get("new") or ""
        self.change.text = ("%s \u2192 %s" % (old, new)) if old else new
        who = (" · " + it["person"]) if it.get("show_person") and it.get("person") else ""
        self.meta.text = "Effective %s · by %s%s" % (state.fmt_date(it["effective"]), it["by"] or "HR", who)
        self.dot.classes.add("k-" + (it.get("kind") or "system"))
