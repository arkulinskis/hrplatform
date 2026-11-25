import json

from anvil import *
from anvil.js import window

from ._anvil_designer import ChartTemplate


class Chart(ChartTemplate):
    """Wraps HR.chart. Set `data` (list of {label, value}); it redraws when shown or when data changes."""

    def __init__(self, **properties):
        self._data, self._kind, self._unit, self._single, self._shown = None, "bar", "", False, False
        super().__init__(**properties)

    def _draw(self):
        if self._shown and self._data is not None:
            window.HR.chart(self.dom_nodes["host"], self._kind, json.dumps(self._data),
                            {"unit": self._unit, "single": self._single})

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

    @property
    def kind(self):
        return self._kind

    @kind.setter
    def kind(self, value):
        self._kind = value or "bar"
        self._draw()

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value):
        self._unit = value or ""

    @property
    def single(self):
        return self._single

    @single.setter
    def single(self, value):
        self._single = bool(value)
