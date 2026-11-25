from anvil import *

from ._anvil_designer import OnboardingTemplate
from ... import router, state


class Onboarding(OnboardingTemplate):
    """#onboarding: the signed-in person's open checklist tasks (tick them here), checklists in progress (onboarding
    and offboarding), recently completed ones, and for HR: start a checklist for someone."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.kind_box.items = [("Onboarding", "onboarding"), ("Offboarding", "offboarding")]
        self.tasks_panel.add_event_handler("x-ticked", self._ticked)
        self._open = 0
        self._load()

    def _load(self):
        d = state.call("onboarding_overview")
        if not d:
            return
        hr = bool(d.get("is_admin"))
        self.start_part.visible = hr
        self.templates_note.visible = hr
        if hr:
            self.person_box.items = [("Choose a person", "")] + [(p["name"], p["id"]) for p in d.get("people") or []]
        tasks = d.get("my_tasks") or []
        for task in tasks:
            task["show_person"] = True
        self._open = len(tasks)
        self.tasks_panel.items = tasks
        self.no_tasks.visible = not tasks
        self._count()
        opened = d.get("open") or []
        on = [c for c in opened if c["kind"] == "onboarding"]
        off = [c for c in opened if c["kind"] != "onboarding"]
        self.on_panel.items, self.no_on.visible = on, not on
        self.off_panel.items, self.no_off.visible = off, not off
        done = d.get("done") or []
        self.done_panel.items, self.no_done.visible = done, not done

    def _count(self):
        self.tasks_title.text = "Your tasks (%d open)" % self._open if self._open else "Your tasks"

    def _ticked(self, task=None, **event_args):
        if task is not None:
            self._open += -1 if task.get("done") else 1
            self._count()

    @handle("start_button", "click")
    def start_button_click(self, **event_args):
        emp = self.person_box.selected_value
        if not emp:
            state.toast("Choose a person first.", "error")
            state.focus(self.person_box)
            return
        self.start_button.enabled, self.start_button.text = False, "Starting..."
        try:
            r = state.call("start_checklist", emp, self.kind_box.selected_value)
        finally:
            self.start_button.enabled, self.start_button.text = True, "Start checklist"
        if r:
            cl = r["checklist"]
            state.toast("%s checklist started for %s" % (cl["kind"].capitalize(), cl["person"]), "ok")
            router.go("checklist", cl["id"])
