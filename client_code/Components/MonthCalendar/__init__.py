import json

from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import MonthCalendarTemplate


class MonthCalendar(MonthCalendarTemplate):
    """Wraps HR.calendar. data = {month, items, holidays, today}; a chip click raises `pick`."""

    def __init__(self, **properties):
        self._data, self._shown = None, False
        self._cb = anvil.js.report_exceptions(self._on_pick)
        super().__init__(**properties)

    def _on_pick(self, req_id):
        self.raise_event("pick", req_id=req_id)

    def _draw(self):
        d = self._data
        if self._shown and d:
            window.HR.calendar(self.dom_nodes["host"], d.get("month"), json.dumps(d.get("items") or []),
                               json.dumps(d.get("holidays") or []), d.get("today") or "", self._cb)

    @handle("", "show")
    def form_show(self, **event_args):
        self._shown = True
        self._draw()

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self._draw()
