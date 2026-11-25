import anvil.server
from anvil import *

from ._anvil_designer import CycleTemplate
from ... import router, state

RATINGS = {1: "Needs improvement", 2: "Developing", 3: "Solid", 4: "Strong", 5: "Outstanding"}


class Cycle(CycleTemplate):
    """#cycle/<id> (HR): progress of one review cycle, the manager-rating spread, everyone's self/manager review
    status with links to each review, and Close cycle (asks first)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._id = args[0] if args else None
        state.heading(self.title_label, 1)
        state.heading(self.denied_h, 1)
        hr = state.is_hr()
        self.denied_box.visible = not hr
        self.main_box.visible = hr
        if hr:
            self._load()

    def _load(self):
        r: dict = {"ok": False}
        if self._id:
            r = anvil.server.call("cycle_status", self._id)
        if not r.get("ok"):
            self.main_box.visible = False
            self.denied_box.visible = True
            self.denied_h.text = "This review cycle isn't here"
            self.denied_text.text = r.get("error") or "It may have been deleted."
            return
        c, rows, dist = r["cycle"], r["rows"], r["distribution"]
        is_open = c["status"] == "open"
        self.title_label.text = c["name"]
        self.meta.text = ("Due " if is_open else "Was due ") + state.fmt_date(c["due"]) + " · " + \
            state.plural(len(c["questions"]), "question")
        self.status.text = "Open" if is_open else "Closed"
        self.status.role = ["badge", "badge-good"] if is_open else ["badge"]
        self.close_button.visible = is_open
        done, total = c["done"], c["total"]
        pct = int(round(100.0 * done / total)) if total else 0
        self.st_done.text, self.st_left.text = str(done), str(total - done)
        self.st_people.text = str(len(rows))
        rated = [x["rating"] for x in rows if x["rating"]]
        self.st_avg.text = ("%.1f" % (float(sum(rated)) / len(rated))) if rated else "-"
        self.bar.style["width"] = "%d%%" % pct
        state.set_attr(self.bar_box, "aria-valuenow", pct)
        state.set_attr(self.bar_box, "aria-label", "%d of %d reviews submitted" % (done, total))
        self.progress_text.text = "%d of %d reviews submitted (%d%%)." % (done, total, pct)
        if is_open and total - done:
            self.progress_text.text += " %s still to write." % state.plural(total - done, "review")
        data = [{"label": str(n), "value": dist.get(str(n), 0)} for n in range(1, 6)]
        self.dist_chart.data = data
        if rated:
            top = max(data, key=lambda x: x["value"])
            n = int(top["label"])
            self.dist_text.text = "Most common rating: %d %s (%s). 1 = Needs improvement, 5 = Outstanding." % (
                n, RATINGS[n], state.plural(top["value"], "person", "people"))
        else:
            self.dist_text.text = "No manager reviews submitted yet. 1 = Needs improvement, 5 = Outstanding."
        self.rows_panel.items = rows
        self.no_rows.visible = not rows

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        if not confirm("Reviews can't be written or changed after this, and people can read their manager's "
                       "review.", title="Close this review cycle?",
                       buttons=[("Cancel", False), ("Close cycle", True)], role="app-dialog"):
            return
        self.close_button.enabled = False
        try:
            r = state.call("close_cycle", self._id)
        finally:
            self.close_button.enabled = True
        if r is not None:
            state.toast("Review cycle closed", "ok")
            self._load()
