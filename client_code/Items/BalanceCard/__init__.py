from anvil import *

from ._anvil_designer import BalanceCardTemplate
from ... import router, state


class BalanceCard(BalanceCardTemplate):
    """A time-off balance: {name, color, allowance, used, pending, left, unlimited}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.dot.classes.add("lv-" + (it.get("color") or "slate"))
        if it["unlimited"]:
            self.left.text, self.unit.text = "%g" % (it["used"] or 0), " used"
            self.meta.text = "No yearly limit" + (" · %s waiting" % state.days(it["pending"]) if it["pending"] else "")
            self.bar_box.visible = False
            return
        allow = it["allowance"] or 1
        self.left.text, self.unit.text = "%g" % it["left"], " left" if it["left"] != 1 else " left"
        self.meta.text = "%s used of %g" % (state.days(it["used"]), it["allowance"]) + (
            " · %s waiting" % state.days(it["pending"]) if it["pending"] else "")
        used = min(100, 100.0 * it["used"] / allow)
        pend = min(100 - used, 100.0 * it["pending"] / allow)
        self.bar_used.style["width"] = "%g%%" % used
        self.bar_pending.style["width"] = "%g%%" % pend
        state.set_attr(self.bar_box, "aria-valuenow", int(used + pend))
        state.set_attr(self.bar_box, "aria-label", "%s: %g of %g days used or requested" % (
            it["name"], it["used"] + it["pending"], it["allowance"]))
