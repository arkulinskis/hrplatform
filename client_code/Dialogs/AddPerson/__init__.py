import anvil.server
from anvil import *

from ._anvil_designer import AddPersonTemplate
from ... import plan, state


class AddPerson(AddPersonTemplate):
    """HR adds someone (a new hire, or an existing colleague). Closes with their card, or None."""

    def __init__(self, **properties):
        super().__init__(**properties)
        d = anvil.server.call("list_people", False)
        self.department.items = d["departments"]
        self.location.items = d["locations"]
        self.manager.items = [("Nobody yet", "")] + [(p["name"], p["id"]) for p in d["people"]]
        self.employment_type.items = ["Full-time", "Part-time", "Contractor", "Intern"]
        state.set_control_attr(self.start_date, "type", "date")
        self.start_date.text = state.today_iso()

    @handle("", "show")
    def form_show(self, **event_args):
        self.first_name.focus()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        if not (self.first_name.text or "").strip():
            self.message.text, self.message.visible = "Add their first name.", True
            return
        data = {"first_name": self.first_name.text, "last_name": self.last_name.text or "",
                "work_email": self.work_email.text or "", "title": self.title.text or "",
                "department": self.department.selected_value, "location": self.location.selected_value,
                "manager": self.manager.selected_value or "", "employment_type": self.employment_type.selected_value,
                "start_date": self.start_date.text or "", "pay_rate": self.pay_rate.text or ""}
        self.save_button.enabled = False
        try:
            r = anvil.server.call("add_person", data, bool(self.onboarding.checked))
        finally:
            self.save_button.enabled = True
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            if r.get("plan"):   # employee 6 and up: the paid plan (only once Stripe is set up)
                plan.need("Employee 6 and up")
            return
        self.raise_event("x-close-alert", value=r["person"])
