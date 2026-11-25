from anvil import *

from ._anvil_designer import CycleRowTemplate
from ... import router, state

STATUS = {"submitted": ("Done", "badge-good"), "todo": ("To do", "badge-warn"), "none": ("No review", "")}
RATINGS = {1: "Needs improvement", 2: "Developing", 3: "Solid", 4: "Strong", 5: "Outstanding"}


class CycleRow(CycleRowTemplate):
    """One person in a review cycle: {person, person_id, initials, tone, department, self, manager, rating,
    self_id, manager_id, reviewer}. Links open each review."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        bits = [b for b in (it.get("department"), ("reviewed by " + it["reviewer"]) if it.get("reviewer") else "") if b]
        self.sub.text = " · ".join(bits)
        for badge, link, kind in ((self.self_badge, self.self_link, "self"), (self.mgr_badge, self.mgr_link, "manager")):
            text, role = STATUS.get(it.get(kind) or "none", STATUS["none"])
            badge.text = text
            badge.role = ["badge", role] if role else ["badge"]
            rid = it.get(kind + "_id")
            link.visible = bool(rid)
            if rid:
                state.set_attr(link, "href", router.href("review", rid))
        n = it.get("rating") or 0
        self.rating.text = ("%d %s" % (n, RATINGS[n])) if n in RATINGS else "Not yet"
        if n not in RATINGS:
            self.rating.role = ["hr-sub"]
