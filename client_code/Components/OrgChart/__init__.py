import json

from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import OrgChartTemplate


class OrgChart(OrgChartTemplate):
    """Wraps HR.orgChart. Draws when shown and whenever data changes; clicking a person raises `select`."""

    def __init__(self, **properties):
        self._data, self._animate, self._focus, self._shown = None, False, "", False
        self._pick = anvil.js.report_exceptions(self._on_pick)
        super().__init__(**properties)

    def _on_pick(self, emp_id):
        self.raise_event("select", emp_id=emp_id)

    def _draw(self):
        if not self._shown or self._data is None:
            return
        window.HR.orgChart(self.dom_nodes["host"], json.dumps(self._data),
                           {"animate": self._animate, "focus": self._focus or None,
                            # the animated landing hero is a picture: no clickable nodes there
                            "onSelect": None if self._animate else self._pick})

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
    def animate(self):
        return self._animate

    @animate.setter
    def animate(self, value):
        self._animate = bool(value)

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        self._focus = value or ""
        self._draw()
