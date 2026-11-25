from anvil import *

from ._anvil_designer import LeaveTypeRowTemplate
from ... import state

# the same list as COLORS in server_code/Leave.py
COLORS = [("Spruce", "spruce"), ("Amber", "amber"), ("Sky", "sky"), ("Plum", "plum"), ("Clay", "clay"),
          ("Slate", "slate")]


class LeaveTypeRow(LeaveTypeRowTemplate):
    """A leave type you can edit: {id (None = new), name, allowance, paid, color}.
    Save raises x-save-type(type_id, data, button); Delete raises x-delete-type(item, button)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self._color = it.get("color") or "spruce"
        self.name_box.text = it.get("name") or ""
        allow = it.get("allowance") or 0
        self.days_box.text = "%g" % allow
        self.paid_box.checked = it.get("paid") is not False
        self.color_drop.items = COLORS
        self.color_drop.selected_value = self._color
        state.set_control_attr(self.color_drop, "aria-label", "Colour")
        state.set_control_attr(self.days_box, "type", "number")
        state.set_control_attr(self.days_box, "min", "0")
        state.set_control_attr(self.days_box, "max", "365")
        self.dot.classes["lv-" + self._color] = True
        self.save_button.text = "Add type" if not it.get("id") else "Save"
        self.delete_button.text = "Delete " + (it.get("name") or "this type") if it.get("id") else "Remove this row"
        if not it.get("id"):
            self.row.classes["new"] = True

    @handle("color_drop", "change")
    def color_drop_change(self, **event_args):
        self.dot.classes["lv-" + self._color] = False
        self._color = self.color_drop.selected_value or "spruce"
        self.dot.classes["lv-" + self._color] = True

    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        data = {"name": (self.name_box.text or "").strip(), "allowance": self.days_box.text or 0,
                "paid": bool(self.paid_box.checked), "color": self._color}
        self.parent.raise_event("x-save-type", type_id=self.item.get("id"), data=data, button=self.save_button)

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        self.parent.raise_event("x-delete-type", item=self.item, button=self.delete_button)

    def focus_name(self):
        self.name_box.focus()
