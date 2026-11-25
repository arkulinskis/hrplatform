import anvil.server
from anvil import *

from ._anvil_designer import JobEditTemplate
from ... import state

TYPES = ["Full-time", "Part-time", "Contractor", "Intern"]
STATUSES = [("Open: on the careers page", "open"), ("Draft: not public yet", "draft"), ("Closed", "closed")]


def _choices(values, current, none_label):
    """DropDown items from a settings list, keeping a current value that is no longer in the list."""
    out = [(none_label, "")] + [(v, v) for v in values]
    if current and current not in values:
        out.append((current, current))
    return out


class JobEdit(JobEditTemplate):
    """Create or edit a job opening (HR). meta = hiring_overview()'s departments, locations and managers.
    Closes with the saved job, or None."""

    def __init__(self, job=None, meta=None, **properties):
        super().__init__(**properties)
        job = job or {}
        meta = meta or {}
        self._id = job.get("id")
        self.heading.text = "Edit job" if self._id else "New job"
        state.heading(self.heading, 2)
        self.title_box.text = job.get("title", "")
        self.dept_box.items = _choices(meta.get("departments") or [], job.get("department"), "No department")
        self.dept_box.selected_value = job.get("department") or ""
        self.loc_box.items = _choices(meta.get("locations") or [], job.get("location"), "No location")
        self.loc_box.selected_value = job.get("location") or ""
        self.type_box.items = [(v, v) for v in TYPES]
        self.type_box.selected_value = job.get("employment_type") or "Full-time"
        self.salary_box.text = job.get("salary_range", "")
        mans = [("Nobody yet", "")] + [(m["name"], m["id"]) for m in meta.get("managers") or []]
        self.manager_box.items = mans
        self.manager_box.selected_value = job.get("manager_id") if job.get("manager_id") in [v for _l, v in mans] else ""
        self.status_box.items = STATUSES
        self.status_box.selected_value = job.get("status") or "open"
        self.desc_box.text = job.get("description", "")
        self.save_button.text = "Save job" if self._id else "Create job"

    @handle("", "show")
    def form_show(self, **event_args):
        self.title_box.focus()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        title = (self.title_box.text or "").strip()
        if len(title) < 2:
            self.message.text, self.message.visible = "Give the job a title.", True
            self.title_box.focus()
            return
        data = {"title": title, "department": self.dept_box.selected_value or "",
                "location": self.loc_box.selected_value or "", "employment_type": self.type_box.selected_value,
                "salary_range": (self.salary_box.text or "").strip(), "manager_id": self.manager_box.selected_value or None,
                "status": self.status_box.selected_value, "description": self.desc_box.text or ""}
        label = self.save_button.text
        self.save_button.enabled, self.save_button.text = False, "Saving..."
        try:
            r = anvil.server.call("save_job", self._id, data)
        finally:
            self.save_button.enabled, self.save_button.text = True, label
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't save.", True
            return
        self.raise_event("x-close-alert", value=r["job"])
