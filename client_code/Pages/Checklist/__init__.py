import anvil.server
from anvil import *

from ._anvil_designer import ChecklistTemplate
from ... import router, state

ROLE_ORDER = ["hr", "it", "manager", "employee"]


class Checklist(ChecklistTemplate):
    """#checklist/<id>: one person's onboarding/offboarding checklist: progress, tasks grouped by who does them
    (HR, IT, manager, the person) with tick boxes, and for HR: add and delete tasks."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._id = args[0] if args else None
        self._cl: dict = {}
        self._tasks: list = []
        self._can_edit = False
        state.heading(self.title_label, 1)
        self._groups = {"hr": (self.g_hr, self.p_hr, self.c_hr), "it": (self.g_it, self.p_it, self.c_it),
                        "manager": (self.g_manager, self.p_manager, self.c_manager),
                        "employee": (self.g_employee, self.p_employee, self.c_employee)}
        for key in ROLE_ORDER:
            panel = self._groups[key][1]
            panel.add_event_handler("x-ticked", self._ticked)
            panel.add_event_handler("x-delete", self._delete)
        state.set_control_attr(self.due_box, "type", "date")
        self._load()

    def _load(self):
        r: dict = anvil.server.call("get_checklist", self._id) if self._id else {"ok": False, "error": "No checklist chosen."}
        ok = bool(r.get("ok"))
        self.found_part.visible, self.missing_part.visible = ok, not ok
        if not ok:
            self.missing_text.text = r.get("error") or "It may have been removed."
            return
        self._cl, self._tasks, self._can_edit = r["checklist"], r["tasks"], bool(r.get("can_edit"))
        roles = r.get("roles") or {}
        self.role_box.items = [(roles.get(k, k), k) for k in ROLE_ORDER]
        self.role_box.selected_value = "hr"
        self._draw_head()
        self._draw_tasks()
        self.add_part.visible = self._can_edit

    def _draw_head(self):
        cl = self._cl
        onboarding = cl["kind"] == "onboarding"
        self.av.initials, self.av.tone = cl.get("initials") or "?", cl.get("tone") or 0
        self.title_label.text = cl.get("title") or ""
        self.person.text = cl.get("person") or ""
        state.set_attr(self.person_link, "href", router.href("person", cl.get("person_id") or ""))
        state.set_attr(self.person_link, "aria-label", "%s's profile" % cl.get("person", ""))
        self.kind_badge.text = "Onboarding" if onboarding else "Offboarding"
        self.kind_badge.role = ["badge", "badge-brand" if onboarding else "badge-warn"]
        when = state.fmt_date(cl.get("date")) if cl.get("date") else "not set"
        self.date_line.text = ("Starts %s" if onboarding else "Last day %s") % when
        if cl.get("title_job"):
            self.date_line.text += " · " + cl["title_job"]
        self.emp_title.text = "New hire" if onboarding else cl.get("person", "").split(" ")[0] or "The person"

    def _draw_progress(self):
        total = len(self._tasks)
        done = len([x for x in self._tasks if x.get("done")])
        late = len([x for x in self._tasks if x.get("overdue") and not x.get("done")])
        pct = int(100.0 * done / total) if total else 0
        self.progress_text.text = "%d of %d done" % (done, total)
        self.bar.style["width"] = "%d%%" % pct
        state.set_attr(self.bar_box, "aria-valuenow", pct)
        state.set_attr(self.bar_box, "aria-label", "Checklist progress: %d%% done" % pct)
        self.late_badge.text, self.late_badge.visible = "%d overdue" % late, late > 0
        if total and done == total:
            self.complete_text.text = "All done. Nice work, everyone."
        elif total:
            left = total - done
            self.complete_text.text = "%s to go." % state.plural(left, "task")
        else:
            self.complete_text.text = "No tasks yet."

    def _draw_tasks(self):
        for task in self._tasks:
            task["can_delete"] = self._can_edit
        for key in ROLE_ORDER:
            box, panel, count = self._groups[key]
            mine = [x for x in self._tasks if x.get("role") == key]
            panel.items = mine
            box.visible = bool(mine)
            done = len([x for x in mine if x.get("done")])
            count.text = "%d of %d" % (done, len(mine))
        self.no_tasks.visible = not self._tasks
        self._draw_progress()

    def _ticked(self, task=None, **event_args):
        if task is None:
            return
        for x in self._tasks:
            if x["id"] == task["id"]:
                x.update(done=task.get("done"), done_by=task.get("done_by"), done_at=task.get("done_at"))
        box, panel, count = self._groups.get(task.get("role"), self._groups["hr"])
        mine = [x for x in self._tasks if x.get("role") == task.get("role")]
        count.text = "%d of %d" % (len([x for x in mine if x.get("done")]), len(mine))
        self._draw_progress()

    def _delete(self, task=None, **event_args):
        if task is None:
            return
        if not confirm('"%s" is removed from this checklist.' % task["title"], title="Delete this task?",
                       buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            return
        if state.call("delete_task", task["id"]):
            self._tasks = [x for x in self._tasks if x["id"] != task["id"]]
            self._draw_tasks()
            state.toast("Task deleted", "ok")
            state.focus(self.task_box if self._can_edit else self.title_label)

    @handle("task_box", "pressed_enter")
    def task_box_pressed_enter(self, **event_args):
        self.add_button_click()

    @handle("add_button", "click")
    def add_button_click(self, **event_args):
        title = (self.task_box.text or "").strip()
        if not title:
            state.toast("Say what needs doing.", "error")
            self.task_box.focus()
            return
        self.add_button.enabled, self.add_button.text = False, "Adding..."
        try:
            r = state.call("add_task", self._id, title, self.role_box.selected_value, self.due_box.text or None)
        finally:
            self.add_button.enabled, self.add_button.text = True, "Add task"
        if r:
            self._tasks.append(r["task"])
            self._draw_tasks()
            self.task_box.text = ""
            self.due_box.text = ""
            state.toast("Task added", "ok")
            self.task_box.focus()
