"""HR reports (HR admins): headcount by team/location/type, headcount trend, hires and leavers, turnover, tenure,
time off taken, hiring funnel, eNPS; CSV exports of the people list and a payroll export for any period."""
import csv
import datetime as dt
import io

import anvil.server
from anvil.tables import app_tables

from . import common as C
from . import Workspace as W
from . import Subscriptions
from . import Perform


def _month_ends(today, n=12):
    out, d = [], today.replace(day=1)
    for _ in range(n):
        out.append(d)
        d = (d - dt.timedelta(days=1)).replace(day=1)
    return list(reversed(out))


def _employed_on(e, day):
    s, end = e["start_date"], e["end_date"]
    return s is not None and s <= day and (end is None or end >= day)


def _counts(rows, key):
    out: dict = {}
    for e in rows:
        k = e[key] or "Not set"
        out[k] = out.get(k, 0) + 1
    return [{"label": k, "value": v} for k, v in sorted(out.items(), key=lambda kv: (-kv[1], kv[0]))]


@anvil.server.callable(require_user=True)
def get_reports():
    cx = W.ctx()
    W.require_admin(cx)
    if not W.paid(cx):
        return C.fail(Subscriptions.LOCKED_MESSAGE)
    today = C.now().date()
    every = list(app_tables.employees.search(company=cx.company))
    current = [e for e in every if e["status"] in ("active", "leave")]
    months = _month_ends(today)
    trend, hires, exits = [], [], []
    for m in months:
        nxt = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        last = min(nxt - dt.timedelta(days=1), today)
        label = m.strftime("%b")
        trend.append({"label": label, "value": len([e for e in every if _employed_on(e, last)])})
        hires.append({"label": label, "value": len([e for e in every if e["start_date"] and m <= e["start_date"] < nxt])})
        exits.append({"label": label, "value": len([e for e in every if e["end_date"] and m <= e["end_date"] < nxt
                                                    and e["end_date"] <= today])})
    year_ago = today - dt.timedelta(days=365)
    leavers = [e for e in every if e["end_date"] and year_ago <= e["end_date"] <= today]
    avg = (sum(t["value"] for t in trend) / len(trend)) if trend else 0
    regretted = len([e for e in leavers if (e["termination"] or {}).get("regretted")])
    tenure = {"< 1 year": 0, "1-2 years": 0, "2-5 years": 0, "5+ years": 0}
    for e in current:
        yrs = (today - e["start_date"]).days / 365.25 if e["start_date"] else 0
        key = "< 1 year" if yrs < 1 else "1-2 years" if yrs < 2 else "2-5 years" if yrs < 5 else "5+ years"
        tenure[key] += 1
    taken: dict = {}
    for r in app_tables.leave_requests.search(company=cx.company, status="approved"):
        if r["start"] is not None and r["start"].year == today.year and r["leave_type"] is not None:
            taken[r["leave_type"]["name"]] = taken.get(r["leave_type"]["name"], 0) + (r["days"] or 0)
    from . import Hiring
    cands = app_tables.candidates.search(company=cx.company)
    funnel = [{"label": Hiring.STAGE_LABELS[s], "value": len([c for c in cands if c["stage"] == s])}
              for s in Hiring.STAGES if s != "rejected"]
    pulse = []
    for s in app_tables.surveys.search(company=cx.company):
        scores = [a["score"] or 0 for a in app_tables.survey_answers.search(survey=s)]
        if len(scores) >= Perform.MIN_ANSWERS:
            pulse.append({"label": s["created"].strftime("%b %Y") if s["created"] else "", "value": Perform.enps(scores),
                          "n": len(scores), "when": C.iso(s["created"])})
    pulse.sort(key=lambda x: x["when"] or "")
    return {"headcount": len(current), "trend": trend, "hires": hires, "exits": exits,
            "by_department": _counts(current, "department"), "by_location": _counts(current, "location"),
            "by_type": _counts(current, "employment_type"),
            "turnover": round(100.0 * len(leavers) / avg, 1) if avg else 0.0, "leavers": len(leavers),
            "regretted": regretted, "new_hires_12m": sum(h["value"] for h in hires),
            "tenure": [{"label": k, "value": v} for k, v in tenure.items()],
            "time_off": [{"label": k, "value": v} for k, v in sorted(taken.items(), key=lambda kv: -kv[1])],
            "funnel": funnel, "pulse": pulse, "currency": cx.company["currency"] or "CAD",
            "on_leave": len([e for e in current if e["status"] == "leave"]),
            "starting": len([e for e in every if e["status"] == "onboarding"])}


def _csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


@anvil.server.callable(require_user=True)
def export_people_csv(include_pay=False):
    cx = W.ctx()
    W.require_admin(cx)
    if not W.paid(cx):
        return C.fail(Subscriptions.LOCKED_MESSAGE)
    head = ["First name", "Last name", "Preferred name", "Work email", "Title", "Department", "Location", "Manager",
            "Employment type", "Status", "Start date", "End date"]
    if include_pay:
        head += ["Pay rate", "Pay period", "Currency", "Pay effective"]
    rows = [head]
    for e in sorted(app_tables.employees.search(company=cx.company), key=lambda e: W.name(e).lower()):
        r = [e["first_name"], e["last_name"], e["preferred_name"], e["work_email"], e["title"], e["department"],
             e["location"], W.name(e["manager"]) if e["manager"] is not None else "", e["employment_type"], e["status"],
             C.iso(e["start_date"]), C.iso(e["end_date"])]
        if include_pay:
            r += [e["pay_rate"], e["pay_period"], e["pay_currency"], C.iso(e["pay_effective"])]
        rows.append(r)
    return C.ok(csv=_csv(rows), name=cx.company["slug"] + "-people.csv", count=len(rows) - 1)


@anvil.server.callable(require_user=True)
def payroll_export(start, end):
    """One row per person employed in the period: pay, changes in the period, paid and unpaid days off."""
    cx = W.ctx()
    W.require_admin(cx)
    if not W.paid(cx):
        return C.fail(Subscriptions.LOCKED_MESSAGE)
    try:
        s, e_ = dt.date.fromisoformat(str(start)[:10]), dt.date.fromisoformat(str(end)[:10])
    except ValueError:
        return C.fail("Choose the first and last day of the pay period.")
    if e_ < s:
        return C.fail("The period ends before it starts.")
    from . import Leave
    hol = Leave.holiday_dates(cx.company)
    rows = [["Employee", "Work email", "Department", "Status", "Start date", "End date", "Pay rate", "Pay period",
             "Currency", "Pay effective", "Paid days off", "Unpaid days off", "Changes in period"]]
    for emp in sorted(app_tables.employees.search(company=cx.company), key=lambda x: W.name(x).lower()):
        if emp["start_date"] is None or emp["start_date"] > e_ or (emp["end_date"] and emp["end_date"] < s):
            continue
        paid = unpaid = 0
        for r in app_tables.leave_requests.search(employee=emp, status="approved"):
            if r["start"] is None or r["end"] is None or r["end"] < s or r["start"] > e_:
                continue
            n = Leave.working_days(max(r["start"], s), min(r["end"], e_), hol)
            if r["leave_type"] is not None and r["leave_type"]["paid"] is False:
                unpaid += n
            else:
                paid += n
        changes = [c for c in app_tables.changes.search(employee=emp)
                   if c["kind"] in ("pay", "job", "status") and c["effective"] and s <= c["effective"] <= e_]
        rows.append([W.name(emp), emp["work_email"], emp["department"], emp["status"], C.iso(emp["start_date"]),
                     C.iso(emp["end_date"]), emp["pay_rate"], emp["pay_period"], emp["pay_currency"],
                     C.iso(emp["pay_effective"]), paid, unpaid,
                     "; ".join("%s: %s -> %s (%s)" % (c["field"], c["old"], c["new"], C.iso(c["effective"]))
                               for c in changes)])
    return C.ok(csv=_csv(rows), name="%s-payroll-%s-to-%s.csv" % (cx.company["slug"], s.isoformat(), e_.isoformat()),
                count=len(rows) - 1)
