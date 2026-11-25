import anvil.js
from anvil import *
from anvil.js import window

from ._anvil_designer import TimeOffTemplate
from ... import state
from ...Dialogs.DecideRequest import DecideRequest
from ...Dialogs.RequestTimeOff import RequestTimeOff

TABS = ["mine", "calendar", "approvals", "holidays"]


def _shift_month(iso, step):
    y, m = int(iso[:4]), int(iso[5:7]) + step
    while m < 1:
        y, m = y - 1, m + 12
    while m > 12:
        y, m = y + 1, m - 12
    return "%04d-%02d-01" % (y, m)


class TimeOff(TimeOffTemplate):
    """#timeoff/<tab>: Mine (balances + my requests), Calendar (who's out per month), Approvals (managers and HR)
    and Holidays (HR adds/deletes). Each tab is its own address; one timeoff_overview call feeds every tab."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._d: dict = {}
        self._month = ""
        self.tab = args[0] if args and args[0] in TABS else "mine"
        state.set_control_attr(self.hol_date_box, "type", "date")
        for panel in (self.mine_panel, self.out_panel, self.appr_panel):
            panel.add_event_handler("x-decide", self._decide)
            panel.add_event_handler("x-cancel", self._cancel)
        self.hol_panel.add_event_handler("x-delete-holiday", self._delete_holiday)
        self._load()

    # ---- data
    def _load(self, month=None):
        d = state.call("timeoff_overview", month or self._month or None)
        if not d:
            return
        self._d = d
        self._month = d["month"]
        can_approve = bool(d.get("is_manager") or d.get("is_admin"))
        self.tab_approvals.visible = can_approve
        if self.tab == "approvals" and not can_approve:
            self.tab = "mine"
        parts = {"mine": self.mine_part, "calendar": self.cal_part, "approvals": self.appr_part,
                 "holidays": self.hol_part}
        tabs = {"mine": self.tab_mine, "calendar": self.tab_calendar, "approvals": self.tab_approvals,
                "holidays": self.tab_holidays}
        for name in TABS:
            parts[name].visible = name == self.tab
            tabs[name].classes["on"] = name == self.tab
            state.set_attr(tabs[name], "aria-current", "page" if name == self.tab else None)
        n = len(d["approvals"])
        self.appr_count.text, self.appr_count.visible = str(n), n > 0
        self._show_mine()
        self._show_calendar()
        self._show_approvals()
        self._show_holidays()

    def _show_mine(self):
        d = self._d
        self.bal_panel.items = d["balances"]
        self.no_bal.visible = not d["balances"]
        mine = sorted(d["mine"], key=lambda r: r.get("created") or "", reverse=True)
        self.mine_panel.items = [dict(r, show_person=False) for r in mine]
        self.no_mine.visible = not mine
        self.request_button.enabled = bool(d["types"])

    def _show_calendar(self):
        d = self._d
        self.month_label.text = state.month_year(self._month)
        self.cal.data = {"month": self._month, "items": d["out"], "today": d["today"],
                         "holidays": [{"date": h["date"], "name": h["name"]} for h in d["holidays"]]}
        self.out_panel.items = [dict(r, show_person=True) for r in d["out"]]
        self.no_out.visible = not d["out"]
        people = len(set(r["person_id"] for r in d["out"]))
        self.out_count.text = ("%s in %s" % (state.plural(people, "person", "people"), self.month_label.text)
                               if d["out"] else "")
        self.this_month_button.visible = self._month[:7] != d["today"][:7]

    def _show_approvals(self):
        items = [dict(r, show_person=True) for r in self._d["approvals"]]
        self.appr_panel.items = items
        self.no_appr.visible = not items

    def _show_holidays(self):
        d = self._d
        today = d["today"]
        hol = d["holidays"]
        upcoming = [h for h in hol if h["date"] >= today]
        past = sorted([h for h in hol if h["date"] < today], key=lambda h: h["date"], reverse=True)
        admin = bool(d.get("is_admin"))
        self.hol_panel.items = [dict(h, can_delete=admin) for h in upcoming + past]
        self.no_hol.visible = not hol
        self.hol_add.visible = admin

    # ---- mine
    @handle("request_button", "click")
    def request_button_click(self, **event_args):
        self.request_button.enabled = False
        try:
            r = alert(RequestTimeOff(types=self._d.get("types"), balances=self._d.get("balances")),
                      buttons=[], role="app-dialog", large=True)
        finally:
            self.request_button.enabled = True
        if r:
            if r.get("mine"):
                state.toast("Request sent: %s, %s" % (state.days(r["days"]), state.date_range(r["start"], r["end"])),
                            "ok")
            else:
                state.toast("Time off added for %s" % r.get("person"), "ok")
            self._load()

    # ---- approve / decline / cancel (events from Items.LeaveRow)
    def _decide(self, req, approve, button=None, **event_args):
        if approve:
            if button is not None:
                button.enabled = False
            r = state.call("decide_request", req["id"], True, "")
            if r:
                state.toast("Approved %s's %s" % (req.get("person"), state.days(req.get("days"))), "ok")
                self._load()
            elif button is not None:
                button.enabled = True
            return
        r = alert(DecideRequest(req=req), buttons=[], role="app-dialog", large=True)
        if r:
            state.toast("Declined. %s can see your note." % (req.get("person") or "They"), "ok")
            self._load()

    def _cancel(self, req, button=None, **event_args):
        what = "%s (%s)" % (state.date_range(req.get("start"), req.get("end")), state.days(req.get("days")))
        if not confirm("The days go back to the balance. This can't be undone, but you can ask again.",
                       title="Cancel time off on %s?" % what,
                       buttons=[("Keep it", False), ("Cancel request", True)], role="app-dialog"):
            return
        if button is not None:
            button.enabled = False
        if state.call("cancel_request", req["id"]):
            state.toast("Request cancelled", "ok")
            self._load()
        elif button is not None:
            button.enabled = True

    # ---- calendar
    def _go_month(self, month):
        for b in (self.prev_button, self.next_button, self.this_month_button):
            b.enabled = False
        try:
            self._load(month)
        finally:
            for b in (self.prev_button, self.next_button, self.this_month_button):
                b.enabled = True

    @handle("prev_button", "click")
    def prev_button_click(self, **event_args):
        self._go_month(_shift_month(self._month, -1))

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        self._go_month(_shift_month(self._month, 1))

    @handle("this_month_button", "click")
    def this_month_button_click(self, **event_args):
        self._go_month(self._d["today"][:8] + "01")

    @handle("cal", "pick")
    def cal_pick(self, req_id=None, **event_args):
        host = anvil.js.get_dom_node(self.out_panel)
        old = host.querySelector(".to-row.to-hl")
        if old:
            old.classList.remove("to-hl")
        el = host.querySelector('[data-req="%s"]' % window.CSS.escape(str(req_id)))
        if el:
            el.classList.add("to-hl")
            el.scrollIntoView({"block": "center", "behavior": "smooth"})
            el.setAttribute("tabindex", "-1")
            getattr(el, "focus")({"preventScroll": True})

    # ---- holidays (HR)
    @handle("hol_name_box", "pressed_enter")
    def hol_name_box_pressed_enter(self, **event_args):
        self.hol_add_button_click()

    @handle("hol_add_button", "click")
    def hol_add_button_click(self, **event_args):
        name = (self.hol_name_box.text or "").strip()
        day = (self.hol_date_box.text or "").strip()
        if not name or not day:
            state.toast("Give the holiday a name and a date.", "error")
            return
        self.hol_add_button.enabled = False
        try:
            r = state.call("save_holiday", name, day)
        finally:
            self.hol_add_button.enabled = True
        if r:
            self.hol_name_box.text, self.hol_date_box.text = "", ""
            state.toast("%s added" % name, "ok")
            self._load()

    def _delete_holiday(self, holiday, button=None, **event_args):
        if not confirm("Requests already made keep their day count; new requests will count this day as a working day.",
                       title="Delete %s (%s)?" % (holiday["name"], state.fmt_date(holiday["date"])),
                       buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            return
        if button is not None:
            button.enabled = False
        if state.call("delete_holiday", holiday["id"]):
            state.toast("%s deleted" % holiday["name"], "ok")
            self._load()
        elif button is not None:
            button.enabled = True
