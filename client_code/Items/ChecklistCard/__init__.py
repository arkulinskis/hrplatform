from anvil import *

from ._anvil_designer import ChecklistCardTemplate
from ... import router, state


class ChecklistCard(ChecklistCardTemplate):
    """An onboarding/offboarding checklist summary: {id, kind, title, done, total, date, overdue, initials, tone}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        state.set_attr(self.link, "href", router.href("checklist", it["id"]))
        when = "Starts" if it["kind"] == "onboarding" else "Last day"
        self.meta.text = "%d of %d done · %s %s" % (it["done"], it["total"], when, state.fmt_date(it["date"]))
        pct = int(100.0 * it["done"] / it["total"]) if it["total"] else 0
        self.bar.style["width"] = "%d%%" % pct
        state.set_attr(self.bar_box, "aria-valuenow", pct)
        state.set_attr(self.bar_box, "aria-label", "%s: %d%% done" % (it["title"], pct))
        if it.get("overdue"):
            self.late.text, self.late.visible = "%d overdue" % it["overdue"], True
