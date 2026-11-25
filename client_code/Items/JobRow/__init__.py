from anvil import *

from ._anvil_designer import JobRowTemplate
from ... import router, state

STATUS = {"open": ("Open", "badge-good"), "draft": ("Draft", "badge-warn"), "closed": ("Closed", "")}


class JobRow(JobRowTemplate):
    """A job opening: {id, title, department, location, employment_type, status, counts?, active?, total?}.
    item["mode"] == "open" (an open role someone can refer a friend to): links to the public careers page in a new
    tab (item["slug"]) and hides the pipeline strip."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        bits = [b for b in (it.get("department"), it.get("location"), it.get("employment_type")) if b]
        self.meta.text = " · ".join(bits) or "No department set"
        text, role = STATUS.get(it.get("status") or "draft", ("Draft", "badge-warn"))
        self.status.text = text
        self.status.role = ["badge"] + ([role] if role else [])
        if it.get("mode") == "open":
            state.set_attr(self.link, "href", router.href("careers", it.get("slug") or ""))
            state.set_attr(self.link, "target", "_blank")
            state.set_attr(self.link, "rel", "noopener")
            self.strip.visible = False
            self.status.visible = False
            self.active.text = it.get("salary_range") or ""
            self.go_text.visible = True
            state.set_attr(self.go_text, "aria-label", "Open on the careers page (new tab)")
            return
        state.set_attr(self.link, "href", router.href("job", it["id"]))
        counts = it.get("counts") or {}
        for key, lab in (("applied", self.n_applied), ("screen", self.n_screen), ("interview", self.n_interview),
                         ("offer", self.n_offer), ("hired", self.n_hired)):
            lab.text = str(counts.get(key, 0))
        n = it.get("active") or 0
        self.active.text = (state.plural(n, "active candidate") if n else "No active candidates") + (
            " · %d in total" % it["total"] if it.get("total") else "")
