from anvil import *

from ._anvil_designer import EventRowTemplate
from ... import router, state


class EventRow(EventRowTemplate):
    """A birthday or work anniversary: {kind, person, person_id, initials, tone, date, in, text}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        state.set_attr(self.link, "href", router.href("person", it["person_id"]))
        self.day.text = str(int(it["date"][8:10]))
        self.mon.text = state.MONTHS[int(it["date"][5:7]) - 1]
        when = "today" if it["in"] == 0 else "tomorrow" if it["in"] == 1 else "in %d days" % it["in"]
        self.what.text = "%s, %s" % (it["text"], when)
        self.icon.classes.add("ic-gift" if it["kind"] == "birthday" else "ic-award")
