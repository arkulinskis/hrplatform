import anvil.server
from anvil import *

from ._anvil_designer import AddAssetTemplate


class AddAsset(AddAssetTemplate):
    """Record equipment given to someone (laptop, badge ...)."""

    def __init__(self, person, **properties):
        super().__init__(**properties)
        self._p = person
        self.heading.text = "Give equipment to %s" % person["first"]
        self.kind.items = ["Laptop", "Phone", "Monitor", "Badge", "Headset", "Vehicle", "Other"]

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        r = anvil.server.call("save_asset", self._p["id"], {"kind": self.kind.selected_value,
                                                           "name": self.item_name.text or "", "serial": self.serial.text or ""})
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=r["asset"])
