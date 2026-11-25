import anvil.server
from anvil import *

from ._anvil_designer import GoalEditTemplate
from ... import state

STATUSES = [("On track", "on_track"), ("At risk", "at_risk"), ("Off track", "off_track"), ("Done", "done")]


class GoalEdit(GoalEditTemplate):
    """Add or update a goal: title, due date, progress 0-100, status; Delete for an existing goal.
    goal = the GoalRow item (None = a new goal for emp_id, or for me). Closes with the saved goal, "deleted" or None."""

    def __init__(self, goal=None, emp_id=None, **properties):
        super().__init__(**properties)
        self._goal: dict = dict(goal or {})
        self._emp_id = emp_id
        self._armed = [False]
        self.status_drop.items = STATUSES
        state.set_control_attr(self.due_box, "type", "date")
        for attr, v in (("type", "number"), ("min", "0"), ("max", "100"), ("step", "5"), ("inputmode", "numeric")):
            state.set_control_attr(self.progress_box, attr, v)
        self._quick = [(self.p0, 0), (self.p25, 25), (self.p50, 50), (self.p75, 75), (self.p100, 100)]
        for btn, n in self._quick:
            btn.add_event_handler("click", self._quick_handler(n))
        g = self._goal
        if g.get("id"):
            self.heading.text = "Update goal"
            self.title_box.text = g.get("title", "")
            self.due_box.text = g.get("due") or ""
            self.status_drop.selected_value = g.get("status") or "on_track"
            self.progress_box.text = str(g.get("progress") or 0)
            self.delete_button.visible = True
            if g.get("person"):
                self.for_who.text, self.for_who.visible = "Goal for %s" % g["person"], True
        else:
            self.status_drop.selected_value = "on_track"
            self.progress_box.text = "0"
        self._mark_quick()

    @handle("", "show")
    def form_show(self, **event_args):
        self.title_box.focus()

    def _quick_handler(self, n):
        def handler(**event_args):
            self.progress_box.text = str(n)
            if n == 100:
                self.status_drop.selected_value = "done"
            self._mark_quick()
        return handler

    def _mark_quick(self):
        try:
            v = int(float(self.progress_box.text or 0))
        except ValueError:
            v = -1
        for btn, n in self._quick:
            btn.role = ["seg", "on"] if n == v else ["seg"]
            state.set_control_attr(btn, "aria-pressed", "true" if n == v else "false")

    @handle("progress_box", "change")
    def progress_box_change(self, **event_args):
        self._mark_quick()

    @handle("title_box", "pressed_enter")
    def title_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    def _error(self, text):
        self.message.text, self.message.visible = text, True

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        title = (self.title_box.text or "").strip()
        if len(title) < 3:
            self._error("Describe the goal in a few words.")
            return
        try:
            progress = int(float(self.progress_box.text or 0))
        except ValueError:
            self._error("Progress is a number from 0 to 100.")
            return
        if progress < 0 or progress > 100:
            self._error("Progress is a number from 0 to 100.")
            return
        self.save_button.enabled = False
        self.save_button.role = ["btn", "btn-primary", "ic-check", "btn-is-busy"]
        try:
            r = anvil.server.call("save_goal", self._goal.get("id"), self._emp_id, title, self.due_box.text or None,
                                  progress, self.status_drop.selected_value or "on_track")
        finally:
            self.save_button.enabled = True
            self.save_button.role = ["btn", "btn-primary", "ic-check"]
        if not r.get("ok"):
            self._error(r.get("error") or "That didn't work.")
            return
        self.raise_event("x-close-alert", value=r["goal"])

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if not self._armed[0]:  # ask inside the dialog (no second pop-up on top of this one)
            self._armed[0] = True
            self.delete_button.text = "Yes, delete it"
            self.delete_button.role = ["btn", "btn-danger", "btn-solid", "ic-trash"]
            self._error("Delete this goal? This can't be undone. Press again to delete.")
            return
        r = anvil.server.call("delete_goal", self._goal.get("id"))
        if not r.get("ok"):
            self._error(r.get("error") or "That didn't work.")
            return
        self.raise_event("x-close-alert", value="deleted")
