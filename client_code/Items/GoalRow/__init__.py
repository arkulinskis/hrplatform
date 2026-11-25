from anvil import *

from ._anvil_designer import GoalRowTemplate
from ... import router, state


class GoalRow(GoalRowTemplate):
    """A goal with a progress bar: {id, title, progress, status, due, person, can_edit?, show_person?}. Update raises x-edit-goal(goal=item) on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        labels = {"on_track": ("On track", "badge-good"), "at_risk": ("At risk", "badge-warn"),
                  "off_track": ("Off track", "badge-bad"), "done": ("Done", "badge-brand")}
        text, role = labels.get(it["status"], ("On track", "badge-good"))
        self.status.text, self.status.role = text, ["badge", role]
        self.bar.style["width"] = "%d%%" % it["progress"]
        state.set_attr(self.bar_box, "aria-valuenow", it["progress"])
        state.set_attr(self.bar_box, "aria-label", "%s: %d%% done" % (it["title"], it["progress"]))
        bits = ["%d%% done" % it["progress"]]
        if it.get("due"):
            bits.append("due " + state.fmt_date(it["due"]))
        if it.get("show_person"):
            bits.insert(0, it["person"])
        self.meta.text = " · ".join(bits)
        self.edit_button.visible = bool(it.get("can_edit"))

    @handle("edit_button", "click")
    def edit_button_click(self, **event_args):
        self.parent.raise_event("x-edit-goal", goal=self.item)
