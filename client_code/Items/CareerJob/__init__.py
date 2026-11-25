from anvil import *

from ._anvil_designer import CareerJobTemplate
from ... import state


class CareerJob(CareerJobTemplate):
    """An open job on the public careers page, as an expandable card: {id, title, department, location,
    employment_type, salary_range, description, open?}. Apply raises x-apply(job) on its panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        bits = [b for b in (it.get("department"), it.get("location"), it.get("employment_type"),
                            it.get("salary_range")) if b]
        self.meta.text = " · ".join(bits)
        self.desc.text = it.get("description") or "The team will share the details when you talk."
        state.set_control_attr(self.apply_button, "aria-label", "Apply for this job: %s" % it["title"])
        if it.get("open"):
            state.set_attr(self.box, "open", "")

    @handle("apply_button", "click")
    def apply_button_click(self, **event_args):
        self.parent.raise_event("x-apply", job=self.item)
