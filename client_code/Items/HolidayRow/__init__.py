import datetime

from anvil import *

from ._anvil_designer import HolidayRowTemplate
from ... import state

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class HolidayRow(HolidayRowTemplate):
    """A public holiday: {id, name, date, can_delete?}. Delete raises x-delete-holiday(holiday, button) on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        iso = it.get("date") or ""
        self.day_num.text = str(int(iso[8:10])) if len(iso) >= 10 else ""
        self.month.text = state.MONTHS[int(iso[5:7]) - 1] + " " + iso[:4] if len(iso) >= 10 else ""
        bits = []
        if len(iso) >= 10:
            d = datetime.date(int(iso[:4]), int(iso[5:7]), int(iso[8:10]))
            bits.append(WEEKDAYS[d.weekday()])
            away = (d - datetime.date.today()).days
            if away == 0:
                bits.append("today")
            elif away == 1:
                bits.append("tomorrow")
            elif away > 1:
                bits.append("in " + state.plural(away, "day"))
            else:
                bits.append("past")
                self.row.classes["past"] = True
            if d.weekday() >= 5:
                bits.append("falls on a weekend")
        self.meta.text = " · ".join(bits)
        self.delete_button.visible = bool(it.get("can_delete"))
        state.set_control_attr(self.delete_button, "aria-label", "Delete %s" % (it.get("name") or "holiday"))

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        self.parent.raise_event("x-delete-holiday", holiday=self.item, button=self.delete_button)
