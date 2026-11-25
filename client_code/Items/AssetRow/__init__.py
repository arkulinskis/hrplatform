from anvil import *

from ._anvil_designer import AssetRowTemplate
from ... import router, state


class AssetRow(AssetRowTemplate):
    """A piece of equipment: {id, kind, name, serial, assigned, returned, can_edit?}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.name.text = "%s: %s" % (it["kind"], it["name"])
        self.meta.text = ("Serial %s · " % it["serial"] if it["serial"] else "") + "given " + state.fmt_date(it["assigned"])
        self.returned.visible = bool(it["returned"])
        self.return_button.visible = not it["returned"] and bool(it.get("can_edit"))

    @handle("return_button", "click")
    def return_button_click(self, **event_args):
        if state.call("return_asset", self.item["id"]) is not None:
            self.parent.raise_event("x-changed")
