import datetime

import anvil.server
from anvil import *

from ._anvil_designer import PersonTemplate
from ... import router, state

TABS = ["about", "job", "time", "goals", "docs", "history"]
ROLE_NAMES = {"admin": "HR admin", "manager": "Manager", "employee": "Employee"}


class Person(PersonTemplate):
    """#person/<id>/<tab>: one employee's profile. What shows depends on the server's permission flags
    (can_private, can_pay, can_team, can_admin): the server never sends fields the viewer may not see."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._id = args[0] if args else state.emp_id()
        self._tab = args[1] if len(args) > 1 and args[1] in TABS else "about"
        self._p: dict = {}
        state.heading(self.name, 1)
        for panel in (self.files_panel, self.assets_panel):
            panel.add_event_handler("x-changed", self._reload)
        self._reload()

    def _reload(self, **event_args):
        r = anvil.server.call("get_person", self._id)
        if not r.get("ok"):
            self.body.visible, self.missing.visible = False, True
            self.missing_text.text = r.get("error") or ""
            return
        self.missing.visible = False
        self._p = r["person"]
        self._draw()

    # ------------------------------------------------------------------ drawing
    def _draw(self):
        p = self._p
        self.avatar.initials, self.avatar.tone = p["initials"], p["tone"]
        self.name.text = p["name"]
        self.title.text = p["title"] or "No job title yet"
        self.status.visible = p["status"] in ("onboarding", "leave", "terminated")
        if self.status.visible:
            state.badge(self.status, p["status"])
        self.you.visible = p["is_me"]
        self.dept.text, self.loc.text = p["department"] or "No team", p["location"] or "No location"
        m = p.get("manager")
        self.mgr_part.visible = bool(m)
        if m:
            self.mgr_name.text = m["name"]
            state.set_attr(self.mgr_link, "href", router.href("person", m["id"]))
        self.tenure.text = self._tenure(p)
        # actions
        self.edit_me_button.visible = p["is_me"]
        self.invite_button.visible = p["can_admin"] and not p["has_account"] and p["status"] != "terminated"
        real = state.me() or {}
        self.preview_button.visible = real.get("real_role") == "admin" and not p["is_me"] and not real.get("viewing_as") \
            and p["status"] != "terminated"
        self.preview_button.text = "Preview as %s" % p["first"]
        acts = []
        if p["can_admin"] and not p["is_me"]:
            if p["status"] == "leave":
                acts.append(("Back from leave", "active"))
            elif p["status"] in ("active", "onboarding"):
                acts.append(("Mark on leave", "leave"))
            if p["status"] != "terminated" and not p.get("end_date"):
                acts.append(("Offboard...", "offboard"))
            if p["status"] == "terminated":
                acts.append(("Rehire (make active)", "active"))
        self.hr_actions.items = [("More actions", "")] + acts
        self.hr_actions.visible = bool(acts)
        if acts:
            state.set_control_attr(self.hr_actions, "aria-label", "More HR actions")
        # tabs
        for name, link in zip(TABS, [self.tab_about, self.tab_job, self.tab_time, self.tab_goals, self.tab_docs,
                                     self.tab_history]):
            state.set_attr(link, "href", router.href("person", p["id"], name))
            link.classes["on"] = name == self._tab
        parts = {"about": self.about_part, "job": self.job_part, "time": self.time_part, "goals": self.goals_part,
                 "docs": self.docs_part, "history": self.history_part}
        for name, part in parts.items():
            part.visible = name == self._tab
        self._about(p)
        self._job(p)
        self._lists(p)

    def _tenure(self, p):
        s = p.get("start_date")
        if not s:
            return "Start date not set"
        today = state.today_iso()
        if s > today:
            return "Starts %s" % state.fmt_date(s)
        d0 = datetime.date(int(s[:4]), int(s[5:7]), int(s[8:10]))
        days = (datetime.date.today() - d0).days
        years, months = days // 365, (days % 365) // 30
        if years:
            return "Joined %s (%s%s)" % (state.fmt_date(s), state.plural(years, "year"),
                                        (", " + state.plural(months, "month")) if months else "")
        return "Joined %s (%s)" % (state.fmt_date(s), state.plural(max(months, 0), "month") if months else "this month")

    def _about(self, p):
        self.about.text = p["about"] or ("%s hasn't written anything about themselves yet." % p["first"])
        self.about.role = ["hr-about"] + ([] if p["about"] else ["hr-muted-text"])
        self.work_email.text = p["work_email"] or "Not set"
        self.pronouns.text = p["pronouns"] or "Not shared"
        if p.get("birthday"):
            self.birthday.text = state.fmt_date(p["birthday"])
        elif p.get("birthday_day"):
            mm, dd = p["birthday_day"].split("-")
            self.birthday.text = "%d %s" % (int(dd), state.MONTHS_LONG[int(mm) - 1])
        else:
            self.birthday.text = "Not shared"
        self.emp_type.text = p["employment_type"] or "Not set"
        self.private_part.visible = p["can_private"]
        if p["can_private"]:
            self.legal_name.text = ("%s %s" % (p.get("first_name", ""), p.get("last_name", ""))).strip() or "Not set"
            self.personal_email.text = p.get("personal_email") or "Not set"
            self.phone.text = p.get("phone") or "Not set"
            self.address.text = p.get("address") or "Not set"
            em = p.get("emergency") or {}
            bits = [x for x in [em.get("name"), em.get("relation"), em.get("phone")] if x]
            self.emergency.text = " · ".join(bits) if bits else "Not set"
        self.kudos_part.visible = bool(p["kudos"])
        self.kudos_panel.items = p["kudos"]
        mgr = p.get("manager")
        self.manager_part.visible = bool(mgr)
        if mgr:
            self.manager_panel.items = [dict(mgr, sub=mgr["title"])]
        self.reports_panel.items = [dict(x, sub=x["title"]) for x in p["reports"]]
        self.reports_part.visible = bool(p["reports"])
        self.reports_count.text = str(len(p["reports"]))
        state.set_attr(self.org_link, "href", router.href("org", p["id"]))

    def _job(self, p):
        self.j_title.text = p["title"] or "Not set"
        self.j_dept.text, self.j_loc.text = p["department"] or "Not set", p["location"] or "Not set"
        self.j_mgr.text = (p.get("manager") or {}).get("name") or "Nobody (top of the org chart)"
        self.j_type.text = p["employment_type"] or "Not set"
        self.j_start.text = state.fmt_date(p["start_date"]) or "Not set"
        self.j_role.text = ROLE_NAMES.get(p["role"], "Employee")
        self.edit_job_button.visible = p["can_edit_job"]
        term = p.get("termination") or {}
        self.term_part.visible = bool(p.get("end_date"))
        if p.get("end_date"):
            reason = term.get("reason") or "Leaving"
            extra = []
            if p["can_admin"]:
                extra.append("regretted" if term.get("regretted") else "not regretted")
                extra.append("eligible for rehire" if term.get("rehire", True) else "not eligible for rehire")
            self.term_text.text = "%s · last day %s%s" % (reason, state.fmt_date(p["end_date"]),
                                                          (" · " + ", ".join(extra)) if extra else "")
        self.pay_part.visible = p["can_pay"]
        self.pay_locked.visible = not p["can_pay"]
        if p["can_pay"]:
            self.pay.text = state.money(p.get("pay_rate"), p.get("pay_currency"), p.get("pay_period"))
            self.pay_since.text = ("Since %s" % state.fmt_date(p["pay_effective"])) if p.get("pay_effective") else ""
            self.edit_pay_button.visible = p["can_admin"]
        self.notes_part.visible = p["can_admin"]
        if p["can_admin"]:
            self.notes.text = p.get("hr_notes") or "No notes."

    def _lists(self, p):
        self.lists_panel.items = p["checklists"]
        self.lists_part.visible = bool(p["checklists"])
        team = p["can_team"]
        self.time_locked.visible = not team
        self.bal_panel.items = p["balances"]
        self.bal_panel.visible = team
        self.time_link.visible = p["is_me"] or state.is_hr() or state.is_manager()
        self.goals_locked.visible = not team
        self.goals_box.visible = team
        self.goals_panel.items = p["goals"]
        self.no_goals.visible = team and not p["goals"]
        priv = p["can_private"]
        self.docs_locked.visible = not priv
        self.docs_box.visible = priv
        self.files_panel.items = p["files"]
        self.no_files.visible = not p["files"]
        self.assets_panel.items = [dict(a, can_edit=p["can_admin"]) for a in p["assets"]]
        self.no_assets.visible = not p["assets"]
        self.asset_button.visible = p["can_admin"]
        self.history_locked.visible = not priv
        self.history_box.visible = priv
        self.history_panel.items = p["history"]
        self.no_history.visible = not p["history"]

    # ------------------------------------------------------------------ actions
    def _edit(self, section):
        from ...Dialogs.EditPerson import EditPerson
        person = alert(EditPerson(person=self._p, section=section), buttons=[], role="app-dialog", large=True)
        if person:
            state.toast("Saved", "ok")
            self._reload()

    @handle("edit_me_button", "click")
    def edit_me_button_click(self, **event_args):
        self._edit("personal")

    @handle("edit_personal_button", "click")
    def edit_personal_button_click(self, **event_args):
        self._edit("personal")

    @handle("edit_job_button", "click")
    def edit_job_button_click(self, **event_args):
        self._edit("job")

    @handle("edit_pay_button", "click")
    def edit_pay_button_click(self, **event_args):
        self._edit("pay")

    @handle("edit_notes_button", "click")
    def edit_notes_button_click(self, **event_args):
        self._edit("notes")

    @handle("invite_button", "click")
    def invite_button_click(self, **event_args):
        r = state.call("invite_code", self._p["id"])
        if r:
            from ...Dialogs.Invite import Invite
            alert(Invite(name=r["name"], code=r["code"]), buttons=[], role="app-dialog")

    @handle("preview_button", "click")
    def preview_button_click(self, **event_args):
        if state.call("view_as", self._p["id"]):
            state.refresh_me()
            state.toast("Previewing as %s. Use Back to me in the yellow bar to stop." % self._p["name"], "ok")
            router.go("home")

    @handle("hr_actions", "change")
    def hr_actions_change(self, **event_args):
        act = self.hr_actions.selected_value
        self.hr_actions.selected_value = ""
        if not act:
            return
        if act == "offboard":
            from ...Dialogs.Terminate import Terminate
            if alert(Terminate(person=self._p), buttons=[], role="app-dialog", large=True):
                state.toast("Offboarding started: a checklist was created.", "ok")
                self._reload()
            return
        if state.call("set_status", self._p["id"], act):
            state.toast("Status updated", "ok")
            self._reload()

    @handle("uploader", "change")
    def uploader_change(self, file, **event_args):
        if file is None:
            return
        r = state.call("upload_file", self._p["id"], file)
        self.uploader.clear()
        if r:
            state.toast("Uploaded %s" % r["file"]["name"], "ok")
            self._reload()

    @handle("asset_button", "click")
    def asset_button_click(self, **event_args):
        from ...Dialogs.AddAsset import AddAsset
        if alert(AddAsset(person=self._p), buttons=[], role="app-dialog"):
            state.toast("Equipment recorded", "ok")
            self._reload()
