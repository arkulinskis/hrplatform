import anvil.server
from anvil import *

from ._anvil_designer import TaskRowTemplate
from ... import router, state


class TaskRow(TaskRowTemplate):
    """A checklist task with a tick box: {id, title, role, role_label, due, done, done_by, done_at, person,
    checklist_id, overdue, can_tick, show_person?, can_delete?}. Ticking saves at once; raises x-ticked(task) and
    x-delete(task) on its panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self._done = bool(it.get("done"))
        self._overdue = bool(it.get("overdue"))
        self.tick.checked = self._done
        state.set_control_attr(self.tick, "aria-label", "Done: %s" % it["title"])
        if not it.get("can_tick"):
            self.tick.enabled = False
            self.tick.tooltip = "For %s" % it.get("role_label", "HR")
            state.set_control_attr(self.tick, "aria-description", "For %s" % it.get("role_label", "HR"))
        self.role_tag.text = it.get("role_label") or "HR"
        self.role_tag.role = ["badge", "ob-role-" + (it.get("role") or "hr")]
        if it.get("show_person"):
            self.person.text = it.get("person") or ""
            state.set_attr(self.person_link, "href", router.href("checklist", it.get("checklist_id") or ""))
        else:
            self.person_link.visible = False
        self.delete_button.visible = bool(it.get("can_delete"))
        state.set_control_attr(self.delete_button, "aria-label", "Delete task: %s" % it["title"])
        self._draw()

    def _draw(self):
        it = self.item
        self.row.classes["done"] = self._done
        self.due.text = ("Due " + state.fmt_date(it["due"], year=False)) if it.get("due") else "No due date"
        self.late.visible = self._overdue and not self._done
        if self._done:
            who = it.get("done_by") or "someone"
            when = state.fmt_date(it.get("done_at"), year=False) if it.get("done_at") else "just now"
            self.done_line.text = "Done by %s, %s" % (who, when)
        self.done_line.visible = self._done

    @handle("tick", "change")
    def tick_change(self, **event_args):
        want = bool(self.tick.checked)
        self.tick.enabled = False
        try:
            r = anvil.server.call("tick_task", self.item["id"], want)
        finally:
            self.tick.enabled = True
        if not r.get("ok"):
            self.tick.checked = self._done
            state.toast(r.get("error") or "That didn't work.", "error")
            return
        task = r["task"]
        self._done = task["done"]
        self.item["done"], self.item["done_by"], self.item["done_at"] = task["done"], task["done_by"], task["done_at"]
        self._overdue = task["overdue"]
        self._draw()
        state.toast("Done: %s" % self.item["title"] if want else "Ticked off again", "ok")
        self.parent.raise_event("x-ticked", task=self.item)

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        self.parent.raise_event("x-delete", task=self.item)
