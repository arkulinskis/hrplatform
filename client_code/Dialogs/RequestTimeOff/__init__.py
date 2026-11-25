import anvil.server
from anvil import *

from ._anvil_designer import RequestTimeOffTemplate
from ... import state


class RequestTimeOff(RequestTimeOffTemplate):
    """Ask for time off. types and balances come from timeoff_overview; HR also picks who it's for (then the leave is
    approved straight away). Closes with the new request dict, or None."""

    def __init__(self, types=None, balances=None, **properties):
        self._types: list = list(types or [])
        self._balances: dict = {}
        for b in balances or []:
            self._balances[b["type_id"]] = b
        self._days = 0
        super().__init__(**properties)
        state.set_control_attr(self.start_box, "type", "date")
        state.set_control_attr(self.end_box, "type", "date")
        self.person_field.visible = state.is_hr()
        if state.is_hr():
            r = anvil.server.call("list_people")
            people = sorted(r.get("people") or [], key=lambda p: p.get("name") or "")
            mine = state.emp_id()
            self.person_drop.items = [("Me", mine)] + [(p["name"], p["id"]) for p in people if p["id"] != mine]
            self.person_drop.selected_value = mine
        self._fill_types()

    def _for_me(self):
        return not state.is_hr() or self.person_drop.selected_value in (None, state.emp_id())

    def _fill_types(self):
        keep = self.type_drop.selected_value
        opts = []
        for ty in self._types:
            if ty.get("unlimited"):
                label = "%s (no yearly limit)" % ty["name"]
            elif self._for_me() and ty["id"] in self._balances:
                left = self._balances[ty["id"]].get("left") or 0
                label = "%s (%s left)" % (ty["name"], state.days(left))
            else:
                label = "%s (%s a year)" % (ty["name"], state.days(ty.get("allowance")))
            opts.append((label, ty["id"]))
        self.type_drop.items = opts
        ids = [ty["id"] for ty in self._types]
        self.type_drop.selected_value = keep if keep in ids else (ids[0] if ids else None)
        self.send_button.text = "Send request" if self._for_me() else "Add time off"

    def _left(self):
        b = self._balances.get(self.type_drop.selected_value)
        if not self._for_me() or b is None or b.get("unlimited"):
            return None
        return b.get("left")

    def _update_count(self):
        a, b = (self.start_box.text or "").strip(), (self.end_box.text or "").strip()
        if a and (not b or b < a):
            self.end_box.text = b = a
        if not (a and b):
            self._days = 0
            self.count_label.text = "Choose the first and last day to see how many working days it takes."
            self.count_label.role = ["to-req-count"]
            return
        n = state.call_quiet("count_days", a, b)
        self._days = n or 0
        left = self._left()
        if not n:
            self.count_label.text = "Those dates are all weekends or holidays, so there's nothing to take."
            self.count_label.role = ["to-req-count", "to-warn"]
        elif left is not None and n > left:
            self.count_label.text = "%s of time off, but only %s left this year." % (state.days(n), state.days(left))
            self.count_label.role = ["to-req-count", "to-warn"]
        else:
            after = (" · %s left afterwards" % state.days(left - n)) if left is not None else ""
            self.count_label.text = "%s of time off%s" % (state.days(n), after)
            self.count_label.role = ["to-req-count", "to-good"]

    @handle("", "show")
    def form_show(self, **event_args):
        state.live(self.count_label)
        state.focus(self.type_drop)

    @handle("person_drop", "change")
    def person_drop_change(self, **event_args):
        self._fill_types()
        self._update_count()

    @handle("type_drop", "change")
    def type_drop_change(self, **event_args):
        self._update_count()

    @handle("start_box", "change")
    def start_box_change(self, **event_args):
        self._update_count()

    @handle("end_box", "change")
    def end_box_change(self, **event_args):
        self._update_count()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    def _error(self, text):
        self.message.text, self.message.visible = text, True

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        a, b = (self.start_box.text or "").strip(), (self.end_box.text or "").strip()
        if not self.type_drop.selected_value:
            return self._error("Choose a type of time off.")
        if not a or not b:
            return self._error("Choose the first and the last day.")
        if b < a:
            return self._error("The last day is before the first day.")
        self.message.visible = False
        emp = None if self._for_me() else self.person_drop.selected_value
        self.send_button.enabled = False
        try:
            r = anvil.server.call("request_time_off", self.type_drop.selected_value, a, b,
                                  self.note_box.text or "", emp)
        finally:
            self.send_button.enabled = True
        if not r.get("ok"):
            return self._error(r.get("error") or "That didn't work.")
        self.raise_event("x-close-alert", value=r["request"])
