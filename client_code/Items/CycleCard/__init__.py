from anvil import *

from ._anvil_designer import CycleCardTemplate
from ... import router, state


class CycleCard(CycleCardTemplate):
    """A review cycle with its progress: {id, name, status, due, done, total, link?} (link = HR can open #cycle/<id>)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        is_open = it["status"] == "open"
        self.status.text = "Open" if is_open else "Closed"
        self.status.role = ["badge", "badge-good"] if is_open else ["badge"]
        total, done = it.get("total") or 0, it.get("done") or 0
        pct = int(round(100.0 * done / total)) if total else 0
        self.bar.style["width"] = "%d%%" % pct
        state.set_attr(self.bar_box, "aria-valuenow", pct)
        state.set_attr(self.bar_box, "aria-label", "%s: %d of %d reviews done" % (it["name"], done, total))
        bits = ["%d of %d reviews done" % (done, total)]
        if it.get("due"):
            bits.append(("due " if is_open else "was due ") + state.fmt_date(it["due"]))
        self.meta.text = " · ".join(bits)
        linked = bool(it.get("link"))
        self.link.visible = linked
        self.name_plain.visible = not linked
        if linked:
            state.set_attr(self.link, "href", router.href("cycle", it["id"]))
