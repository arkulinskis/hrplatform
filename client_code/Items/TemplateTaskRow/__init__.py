from anvil import *

from ._anvil_designer import TemplateTaskRowTemplate
from ... import state

# TASK_ROLES in server_code/Workspace.py
ROLES = [("HR", "hr"), ("Manager", "manager"), ("IT", "it"), ("New hire", "employee")]


class TemplateTaskRow(TemplateTaskRowTemplate):
    """One editable checklist-template task: {title, role, day, list}. value() reads it back;
    the trash button raises x-remove-task(row) on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.title_box.text = it.get("title") or ""
        self.role_drop.items = ROLES
        self.role_drop.selected_value = it.get("role") if it.get("role") in [v for (lbl, v) in ROLES] else "hr"
        self.day_box.text = str(it.get("day") or 0)
        state.set_control_attr(self.day_box, "type", "number")
        state.set_control_attr(self.day_box, "min", "-60")
        state.set_control_attr(self.day_box, "max", "120")
        self.remove_button.text = "Remove " + (it.get("title") or "this task")

    def value(self):
        try:
            day = int(float(self.day_box.text or 0))
        except ValueError:
            day = 0
        return {"title": (self.title_box.text or "").strip(), "role": self.role_drop.selected_value or "hr",
                "day": day, "list": self.item.get("list")}

    def focus_title(self):
        self.title_box.focus()

    @handle("remove_button", "click")
    def remove_button_click(self, **event_args):
        self.parent.raise_event("x-remove-task", row=self)
