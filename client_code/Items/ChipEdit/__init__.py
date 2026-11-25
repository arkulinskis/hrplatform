from anvil import *

from ._anvil_designer import ChipEditTemplate
from ... import state


class ChipEdit(ChipEditTemplate):
    """An editable list entry: {text, kind}. The x raises x-remove-chip(text, kind) on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        text = self.item.get("text") or ""
        self.remove_button.text = "Remove " + text
        state.set_attr(self.remove_button, "data-key", text)

    @handle("remove_button", "click")
    def remove_button_click(self, **event_args):
        self.parent.raise_event("x-remove-chip", text=self.item.get("text"), kind=self.item.get("kind"))
