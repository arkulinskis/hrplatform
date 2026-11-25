import anvil.server
from anvil import *

from ._anvil_designer import AddCandidateTemplate
from ... import state

SOURCES = ["Careers page", "Referral", "LinkedIn", "Job board", "Agency", "Other"]


class AddCandidate(AddCandidateTemplate):
    """Add someone to a job's pipeline by hand (a referral, someone from LinkedIn). Closes with the new candidate,
    or None."""

    def __init__(self, job=None, sources=None, **properties):
        super().__init__(**properties)
        self._job = job or {}
        self.job_line.text = "For %s. They start in Applied." % self._job.get("title", "this job")
        self.source_box.items = [(s, s) for s in (sources or SOURCES)]
        self.source_box.selected_value = "Referral"
        state.set_control_attr(self.name_box, "autocomplete", "off")

    @handle("", "show")
    def form_show(self, **event_args):
        self.name_box.focus()

    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        if len(name) < 2:
            self.message.text, self.message.visible = "Add the candidate's name.", True
            self.name_box.focus()
            return
        data = {"name": name, "email": (self.email_box.text or "").strip(), "phone": self.phone_box.text or "",
                "link": (self.link_box.text or "").strip(), "cover": self.cover_box.text or "",
                "source": self.source_box.selected_value}
        self.save_button.enabled, self.save_button.text = False, "Adding..."
        try:
            r = anvil.server.call("add_candidate", self._job.get("id"), data)
        finally:
            self.save_button.enabled, self.save_button.text = True, "Add candidate"
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=r["candidate"])
