import anvil.server
from anvil import *

from ._anvil_designer import EditPersonTemplate
from ... import state

TITLES = {"personal": "Personal details", "job": "Job details", "pay": "Change pay", "notes": "HR notes"}


class EditPerson(EditPersonTemplate):
    """Edit one section of a profile (personal / job / pay / notes). Job and pay changes ask for the date they take
    effect, so the change history stays right. Closes with the updated person, or None."""

    def __init__(self, person, section, **properties):
        super().__init__(**properties)
        self._p = person
        self._section = section
        self.heading.text = "%s: %s" % (TITLES.get(section, "Edit"), person["name"])
        for name, part in (("personal", self.personal_part), ("job", self.job_part), ("pay", self.pay_part),
                           ("notes", self.notes_part)):
            part.visible = name == section
        self.eff_part.visible = section in ("job", "pay")
        for box in (self.birthday, self.start_date, self.effective):
            state.set_control_attr(box, "type", "date")
        self.effective.text = state.today_iso()
        o = person.get("options") or {}
        if section == "personal":
            for f in ("first_name", "last_name", "preferred_name", "pronouns", "personal_email", "phone", "address",
                      "about"):
                getattr(self, f).text = person.get(f) or ""
            self.birthday.text = person.get("birthday") or ""
            em = person.get("emergency") or {}
            self.em_name.text, self.em_relation.text, self.em_phone.text = em.get("name", ""), em.get("relation", ""), em.get("phone", "")
            state.set_control_attr(self.personal_email, "autocomplete", "email")
            state.set_control_attr(self.phone, "autocomplete", "tel")
        elif section == "job":
            self.title.text, self.work_email.text = person["title"], person["work_email"]
            self.department.items = self._with(o.get("departments", []), person["department"])
            self.department.selected_value = person["department"] or None
            self.location.items = self._with(o.get("locations", []), person["location"])
            self.location.selected_value = person["location"] or None
            self.manager.items = [("Nobody (top of the chart)", "")] + [(m["name"], m["id"]) for m in o.get("managers", [])]
            self.manager.selected_value = person["manager_id"] or ""
            self.employment_type.items = o.get("types", [])
            self.employment_type.selected_value = person["employment_type"] or "Full-time"
            self.start_date.text = person["start_date"] or ""
            self.role.items = [("Employee", "employee"), ("Manager", "manager"), ("HR admin (sees everything)", "admin")]
            self.role.selected_value = person["role"]
        elif section == "pay":
            self.pay_rate.text = "" if person.get("pay_rate") is None else "%g" % person["pay_rate"]
            self.pay_period.items = [("Year", "year"), ("Month", "month"), ("Hour", "hour")]
            self.pay_period.selected_value = person.get("pay_period") or "year"
            self.pay_currency.items = o.get("currencies", ["CAD"])
            self.pay_currency.selected_value = person.get("pay_currency") or (state.me() or {}).get("currency") or "CAD"
        else:
            self.hr_notes.text = person.get("hr_notes") or ""

    def _with(self, options, current):
        opts = list(options)
        if current and current not in opts:
            opts.append(current)
        return opts

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    def _data(self):
        s = self._section
        if s == "personal":
            d = {f: getattr(self, f).text or "" for f in ("first_name", "last_name", "preferred_name", "pronouns",
                                                          "personal_email", "phone", "address", "about", "birthday")}
            d["emergency"] = {"name": self.em_name.text or "", "relation": self.em_relation.text or "",
                              "phone": self.em_phone.text or ""}
            return d
        if s == "job":
            return {"title": self.title.text or "", "work_email": self.work_email.text or "",
                    "department": self.department.selected_value or "", "location": self.location.selected_value or "",
                    "manager": self.manager.selected_value or "", "employment_type": self.employment_type.selected_value,
                    "start_date": self.start_date.text or "", "role": self.role.selected_value}
        if s == "pay":
            return {"pay_rate": self.pay_rate.text, "pay_period": self.pay_period.selected_value,
                    "pay_currency": self.pay_currency.selected_value}
        return {"hr_notes": self.hr_notes.text or ""}

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        self.save_button.enabled = False
        try:
            r = anvil.server.call("update_person", self._p["id"], self._section, self._data(), self.effective.text or None)
        finally:
            self.save_button.enabled = True
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=r["person"])
