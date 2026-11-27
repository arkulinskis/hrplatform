import datetime

from anvil import *

from ._anvil_designer import ReportsTemplate
from ... import plan, state, subscription


def _top(rows):
    return max(rows, key=lambda r: r["value"]) if rows else None


def _total(rows):
    return sum(r["value"] or 0 for r in rows)


def _num(n):
    return ("%g" % n) if isinstance(n, float) else str(n)


def takeaways(d):
    """One plain-language line per chart (pure Python, so it is easy to test and tweak)."""
    out = {}
    trend = d.get("trend") or []
    if len(trend) >= 2:
        a, b = trend[0]["value"], trend[-1]["value"]
        if b > a:
            out["trend"] = "Up from %d to %d people over the last 12 months." % (a, b)
        elif b < a:
            out["trend"] = "Down from %d to %d people over the last 12 months." % (a, b)
        else:
            out["trend"] = "Steady at %d people over the last 12 months." % b
    else:
        out["trend"] = "Not enough history yet."
    hires, leavers = d.get("new_hires_12m") or 0, d.get("leavers") or 0
    if hires or leavers:
        net = hires - leavers
        out["flow"] = "%s joined and %s left in the last 12 months (net %s%d)." % (
            state.plural(hires, "person", "people"), state.plural(leavers, "person", "people"),
            "+" if net > 0 else "", net)
    else:
        out["flow"] = "Nobody joined or left in the last 12 months."
    head = d.get("headcount") or 0
    dept = _top(d.get("by_department") or [])
    out["dept"] = ("%s is the biggest team (%s)." % (dept["label"], state.plural(dept["value"], "person", "people"))
                   if dept else "No departments yet.")
    loc = _top(d.get("by_location") or [])
    if loc and len(d.get("by_location") or []) == 1:
        out["loc"] = "Everyone works in %s." % loc["label"]
    elif loc:
        where = "remotely" if loc["label"].lower() == "remote" else "in " + loc["label"]
        if loc["value"] * 2 > head:
            out["loc"] = "Most people work %s (%d of %d)." % (where, loc["value"], head)
        else:
            out["loc"] = "The biggest group works %s (%d of %d)." % (where, loc["value"], head)
    else:
        out["loc"] = "No locations yet."
    typ = _top(d.get("by_type") or [])
    out["type"] = ("%d of %d people are %s." % (typ["value"], head, typ["label"].lower()) if typ
                   else "No employment types yet.")
    ten = _top([t for t in (d.get("tenure") or []) if t["value"]])
    if ten:
        out["tenure"] = ("Most people have been here less than a year (%d)." % ten["value"] if ten["label"] == "< 1 year"
                         else "The biggest group has been here %s (%d people)." % (ten["label"], ten["value"]))
    else:
        out["tenure"] = "No start dates yet."
    off = d.get("time_off") or []
    if off:
        out["timeoff"] = "%s is the most used: %s d of %s d taken so far this year." % (
            off[0]["label"], _num(off[0]["value"]), _num(_total(off)))
    else:
        out["timeoff"] = "No approved time off this year yet."
    funnel = d.get("funnel") or []
    total = _total(funnel)
    if total:
        late = [f for f in funnel if f["label"] in ("Offer", "Hired")]
        out["funnel"] = "%s in the pipeline; %d at offer or hired." % (
            state.plural(total, "candidate"), _total(late))
    else:
        out["funnel"] = "No candidates yet. Open a job to start hiring."
    pulse = d.get("pulse") or []
    if pulse:
        last = pulse[-1]
        sign = "+" if last["value"] > 0 else ""
        line = "Latest eNPS is %s%d (from %d answers)" % (sign, last["value"], last["n"])
        if len(pulse) >= 2:
            diff = last["value"] - pulse[-2]["value"]
            line += ", %s %d since the one before." % ("up" if diff >= 0 else "down", abs(diff)) if diff else \
                ", the same as the one before."
        else:
            line += "."
        out["enps"] = line
    else:
        out["enps"] = "Shows after a pulse survey gets at least 3 answers."
    return out


class Reports(ReportsTemplate):
    """#reports (HR only): headline numbers, nine charts each with a one-line takeaway, and CSV exports
    (people list with or without pay, payroll for any period)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        hr = state.is_hr()
        paid = subscription.active()   # always True while the paid plan is off
        self.denied_box.visible = not hr
        self.locked_box.visible = hr and not paid
        self.main_box.visible = hr and paid
        for box in (self.start_box, self.end_box):
            state.set_control_attr(box, "type", "date")
        today = datetime.date.today()
        first = today.replace(day=1)
        last = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        self.start_box.text, self.end_box.text = first.isoformat(), last.isoformat()
        if hr and paid:
            self._load()

    @handle("plan_button", "click")
    def plan_button_click(self, **event_args):
        plan.need("Reports and exports")

    def _load(self):
        d = state.call("get_reports")
        if d is None:
            return
        self.st_head.text = str(d["headcount"])
        self.st_starting.text = str(d["starting"])
        self.st_leave.text = str(d["on_leave"])
        self.st_turnover.text = "%g%%" % d["turnover"]
        self.st_hires.text = str(d["new_hires_12m"])
        self.st_regretted.text = str(d["regretted"])
        self.trend_chart.data = d["trend"]
        self.hires_chart.data = d["hires"]
        self.exits_chart.data = d["exits"]
        self.dept_chart.data = d["by_department"]
        self.loc_chart.data = d["by_location"]
        self.type_chart.data = d["by_type"]
        self.tenure_chart.data = d["tenure"]
        self.timeoff_chart.data = d["time_off"]
        self.funnel_chart.data = d["funnel"]
        self.enps_chart.data = [{"label": p["label"], "value": p["value"]} for p in d["pulse"]]
        t = takeaways(d)
        for key, label in (("trend", self.trend_text), ("flow", self.flow_text), ("dept", self.dept_text),
                           ("loc", self.loc_text), ("type", self.type_text), ("tenure", self.tenure_text),
                           ("timeoff", self.timeoff_text), ("funnel", self.funnel_text), ("enps", self.enps_text)):
            label.text = t.get(key, "")

    def _busy(self, btn, on):
        btn.role = ["btn", "ic-download"] + (["btn-is-busy"] if on else [])
        btn.enabled = not on

    @handle("people_button", "click")
    def people_button_click(self, **event_args):
        self._busy(self.people_button, True)
        try:
            r = state.call("export_people_csv", bool(self.pay_box.checked))
        finally:
            self._busy(self.people_button, False)
        if r is not None:
            state.download_text(r["csv"], r["name"], "text/csv")
            state.toast("Downloaded %s" % state.plural(r["count"], "person", "people"), "ok")

    @handle("payroll_button", "click")
    def payroll_button_click(self, **event_args):
        s, e = self.start_box.text or "", self.end_box.text or ""
        if not s or not e:
            state.toast("Choose the first and last day of the pay period.", "error")
            return
        if e < s:
            state.toast("The period ends before it starts.", "error")
            return
        self._busy(self.payroll_button, True)
        try:
            r = state.call("payroll_export", s, e)
        finally:
            self._busy(self.payroll_button, False)
        if r is not None:
            state.download_text(r["csv"], r["name"], "text/csv")
            state.toast("Payroll export downloaded: %s" % state.plural(r["count"], "row"), "ok")
