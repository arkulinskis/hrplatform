from anvil import *

from ._anvil_designer import SettingsTemplate
from ... import state
from ...Dialogs.ImportPeople import ImportPeople, download_template

TABS = ["company", "timeoff", "checklists", "data", "audit"]
CURRENCIES = ["CAD", "USD", "EUR", "GBP", "AUD"]  # the same list as CURRENCIES in server_code/Workspace.py
LIST_NAMES = {"departments": "Departments", "locations": "Locations", "values": "Company values"}


class Settings(SettingsTemplate):
    """#settings/<tab> (HR admins): Company (name, country, currency + departments/locations/values chip lists),
    Time off (leave types), Checklists (onboarding/offboarding templates), People data (import, export, remove the
    sample) and the Audit log. Everyone else sees a friendly "only HR" box."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._lists: dict = {"departments": [], "locations": [], "values": []}
        self._types: list = []
        self._audit: list = []
        self._total = 0
        self.tab = args[0] if args and args[0] in TABS else "company"
        admin = state.is_hr()
        self.no_access.visible = not admin
        self.admin_part.visible = admin
        if not admin:
            return
        parts = {"company": self.company_part, "timeoff": self.timeoff_part, "checklists": self.checklists_part,
                 "data": self.data_part, "audit": self.audit_part}
        tabs = {"company": self.tab_company, "timeoff": self.tab_timeoff, "checklists": self.tab_checklists,
                "data": self.tab_data, "audit": self.tab_audit}
        for name in TABS:
            parts[name].visible = name == self.tab
            tabs[name].classes["on"] = name == self.tab
            state.set_attr(tabs[name], "aria-current", "page" if name == self.tab else None)
        self._panels = {"departments": self.dept_panel, "locations": self.loc_panel, "values": self.val_panel}
        self._boxes = {"departments": self.dept_box, "locations": self.loc_box, "values": self.val_box}
        self._adds = {"departments": self.dept_add, "locations": self.loc_add, "values": self.val_add}
        for kind, panel in self._panels.items():
            panel.add_event_handler("x-remove-chip", self._remove_chip)
            state.set_control_attr(self._boxes[kind], "aria-label", "New " + LIST_NAMES[kind].lower().rstrip("s"))
        self.types_panel.add_event_handler("x-save-type", self._save_type)
        self.types_panel.add_event_handler("x-delete-type", self._delete_type)
        self.onb_panel.add_event_handler("x-remove-task", self._remove_task)
        self.off_panel.add_event_handler("x-remove-task", self._remove_task)
        state.set_control_attr(self.filter_box, "aria-label", "Filter the audit log by person or field")
        getattr(self, "_load_" + self.tab)()

    # ================================================================ company
    def _load_company(self):
        d = state.call("get_company")
        if not d:
            return
        self.name_box.text = d["name"]
        self.country_box.text = d["country"]
        self.currency_drop.items = CURRENCIES
        self.currency_drop.selected_value = d["currency"] if d["currency"] in CURRENCIES else "CAD"
        for kind in self._lists:
            self._lists[kind] = list(d.get(kind) or [])
            self._show_list(kind)

    def _show_list(self, kind):
        self._panels[kind].items = [{"text": x, "kind": kind} for x in self._lists[kind]]

    @handle("save_company_button", "click")
    def save_company_button_click(self, **event_args):
        self.save_company_button.enabled = False
        try:
            r = state.call("save_company", self.name_box.text or "", self.country_box.text or "",
                           self.currency_drop.selected_value)
        finally:
            self.save_company_button.enabled = True
        if r:
            state.toast("Company saved", "ok")
            if state.me() and r["company"]["name"] != (state.me() or {}).get("company"):
                state.refresh_me()

    def _save_list(self, kind, items, button=None, done=""):
        if button is not None:
            button.enabled = False
        try:
            r = state.call("save_list", kind, items)
        finally:
            if button is not None:
                button.enabled = True
        if not r:
            return False
        self._lists[kind] = list(r["company"].get(kind) or [])
        self._show_list(kind)
        state.toast(done or (LIST_NAMES[kind] + " saved"), "ok")
        return True

    def _add_chip(self, kind):
        box = self._boxes[kind]
        text = (box.text or "").strip()
        if not text:
            state.toast("Type a name first.", "error")
            box.focus()
            return
        if text.lower() in [x.lower() for x in self._lists[kind]]:
            state.toast("%s is already on the list." % text, "error")
            return
        if self._save_list(kind, self._lists[kind] + [text], self._adds[kind], "Added %s" % text):
            box.text = ""
            box.focus()

    def _remove_chip(self, text, kind, **event_args):
        items = [x for x in self._lists[kind] if x != text]
        if not items:
            state.toast("Keep at least one.", "error")
            return
        if self._save_list(kind, items, None, "Removed %s" % text):
            self._boxes[kind].focus()

    @handle("dept_add", "click")
    def dept_add_click(self, **event_args):
        self._add_chip("departments")

    @handle("dept_box", "pressed_enter")
    def dept_box_pressed_enter(self, **event_args):
        self._add_chip("departments")

    @handle("loc_add", "click")
    def loc_add_click(self, **event_args):
        self._add_chip("locations")

    @handle("loc_box", "pressed_enter")
    def loc_box_pressed_enter(self, **event_args):
        self._add_chip("locations")

    @handle("val_add", "click")
    def val_add_click(self, **event_args):
        self._add_chip("values")

    @handle("val_box", "pressed_enter")
    def val_box_pressed_enter(self, **event_args):
        self._add_chip("values")

    # ================================================================ time off types
    def _load_timeoff(self):
        d = state.call("timeoff_overview", None)
        if d:
            self._show_types(d["types"])

    def _show_types(self, types):
        self._types = list(types)
        self.types_panel.items = self._types
        self.no_types.visible = not self._types

    @handle("add_type_button", "click")
    def add_type_button_click(self, **event_args):
        if not any(not ty.get("id") for ty in self._types):
            used = [ty.get("color") for ty in self._types]
            color = next((c for c in ["sky", "plum", "clay", "amber", "slate", "spruce"] if c not in used), "sky")
            self._show_types(self._types + [{"id": None, "name": "", "allowance": 0, "paid": True, "color": color}])
        rows = self.types_panel.get_components()
        if rows:
            last = rows[-1]
            if hasattr(last, "focus_name"):
                getattr(last, "focus_name")()

    def _save_type(self, type_id, data, button=None, **event_args):
        if len(data.get("name") or "") < 2:
            state.toast("Give the type a name (e.g. Vacation).", "error")
            return
        if button is not None:
            button.enabled = False
        try:
            r = state.call("save_leave_type", type_id, data["name"], data["allowance"], data["paid"], data["color"])
        finally:
            if button is not None:
                button.enabled = True
        if r:
            pending_new = [ty for ty in self._types if not ty.get("id")] if type_id else []
            self._show_types(r["types"] + pending_new)
            state.toast("%s %s" % (data["name"], "saved" if type_id else "added"), "ok")

    def _delete_type(self, item, button=None, **event_args):
        if not item.get("id"):
            self._show_types([ty for ty in self._types if ty.get("id")])
            return
        if not confirm("People can't pick it any more. Types that have been used can't be deleted.",
                       title="Delete %s?" % item["name"], buttons=[("Cancel", False), ("Delete", True)],
                       role="app-dialog"):
            return
        if button is not None:
            button.enabled = False
        r = state.call("delete_leave_type", item["id"])
        if button is not None:
            button.enabled = True
        if r:
            self._show_types(r["types"] + [ty for ty in self._types if not ty.get("id")])
            state.toast("%s deleted" % item["name"], "ok")

    # ================================================================ checklist templates
    def _load_checklists(self):
        d = state.call("get_company")
        if not d:
            return
        self._show_tasks("onboarding", [dict(x, list="onboarding") for x in d.get("onboarding") or []])
        self._show_tasks("offboarding", [dict(x, list="offboarding") for x in d.get("offboarding") or []])

    def _task_panel(self, which):
        return self.onb_panel if which == "onboarding" else self.off_panel

    def _show_tasks(self, which, rows):
        self._task_panel(which).items = rows
        (self.no_onb if which == "onboarding" else self.no_off).visible = not rows

    def _task_values(self, which):
        out = []
        for c in self._task_panel(which).get_components():
            if hasattr(c, "value"):
                out.append(getattr(c, "value")())
        return out

    def _add_task(self, which):
        rows = self._task_values(which) + [{"title": "", "role": "hr", "day": 0, "list": which}]
        self._show_tasks(which, rows)
        comps = self._task_panel(which).get_components()
        if comps and hasattr(comps[-1], "focus_title"):
            getattr(comps[-1], "focus_title")()

    def _remove_task(self, row, **event_args):
        which = row.item.get("list") or "onboarding"
        comps = self._task_panel(which).get_components()
        rows = [getattr(c, "value")() for c in comps if c is not row and hasattr(c, "value")]
        self._show_tasks(which, rows)

    def _save_tasks(self, which, button):
        rows = self._task_values(which)
        clean = [{"title": x["title"], "role": x["role"], "day": x["day"]} for x in rows if x["title"]]
        if button is not None:
            button.enabled = False
        try:
            r = state.call("save_list", which, clean)
        finally:
            button.enabled = True
        if r:
            self._show_tasks(which, [dict(x, list=which) for x in r["company"].get(which) or []])
            state.toast("%s checklist saved (%s)" % (which.capitalize(), state.plural(len(clean), "task")), "ok")

    @handle("onb_add", "click")
    def onb_add_click(self, **event_args):
        self._add_task("onboarding")

    @handle("off_add", "click")
    def off_add_click(self, **event_args):
        self._add_task("offboarding")

    @handle("onb_save", "click")
    def onb_save_click(self, **event_args):
        self._save_tasks("onboarding", self.onb_save)

    @handle("off_save", "click")
    def off_save_click(self, **event_args):
        self._save_tasks("offboarding", self.off_save)

    # ================================================================ people data
    def _load_data(self):
        self.sample_box.visible = bool((state.me() or {}).get("has_sample"))

    @handle("import_button", "click")
    def import_button_click(self, **event_args):
        r = alert(ImportPeople(), buttons=[], role="app-dialog", large=True)
        if r:
            msg = "Added %s" % state.plural(r["added"], "person", "people")
            if r.get("skipped"):
                msg += " (%s skipped)" % state.plural(r["skipped"], "row")
            state.toast(msg, "ok")

    @handle("template_button", "click")
    def template_button_click(self, **event_args):
        download_template()

    @handle("export_button", "click")
    def export_button_click(self, **event_args):
        self.export_button.enabled = False
        try:
            r = state.call("export_company")
        finally:
            self.export_button.enabled = True
        if r:
            state.download_text(r["json"], r["name"], "application/json")
            state.toast("Export downloaded", "ok")

    @handle("sample_button", "click")
    def sample_button_click(self, **event_args):
        if not confirm("Every sample person, request, review and post is deleted. People and data you added stay.",
                       title="Remove the sample data?", buttons=[("Keep it", False), ("Remove sample data", True)],
                       role="app-dialog"):
            return
        self.sample_button.enabled = False
        try:
            r = state.call("remove_sample")
        finally:
            self.sample_button.enabled = True
        if r:
            state.refresh_me()
            self.sample_box.visible = False
            state.toast("Sample data removed (%s)" % state.plural(r.get("removed") or 0, "row"), "ok")

    # ================================================================ audit log
    def _load_audit(self):
        d = state.call("audit_log", 300)
        if not d:
            return
        self._audit = [dict(x, show_person=True) for x in d["items"]]
        self._total = d["total"]
        self._show_audit()

    def _show_audit(self):
        q = (self.filter_box.text or "").strip().lower()
        if q:
            rows = [x for x in self._audit if q in ("%s %s %s" % (x.get("person") or "", x.get("field") or "",
                                                                  x.get("by") or "")).lower()]
        else:
            rows = self._audit
        self.audit_panel.items = rows
        self.no_audit.visible = not self._audit
        self.no_match.visible = bool(self._audit) and not rows
        shown = state.plural(len(rows), "change")
        total = self._total
        self.audit_count.text = shown + ((" of %d" % total) if (q or total > len(self._audit)) else "")

    @handle("filter_box", "change")
    def filter_box_change(self, **event_args):
        self._show_audit()
