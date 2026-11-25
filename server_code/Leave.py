"""Time off: leave types with yearly allowances, public holidays, requests counted in working days, approvals by
the person's manager (or HR), balances, and the who's-out calendar.

Allowance 0 means "no limit" (unpaid leave, for example). Requests never count weekends or the company's holidays.
Colleagues see that someone is out; the type (e.g. sick) is shown only to the person, their managers and HR."""
import datetime as dt

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables
import anvil.tables.query as q

from . import common as C
from . import Workspace as W

COLORS = ["spruce", "amber", "sky", "plum", "clay", "slate"]


def _date(v):
    try:
        return dt.date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def holiday_dates(company, year=None):
    out = set()
    for h in app_tables.holidays.search(company=company):
        if h["date"] is not None and (year is None or h["date"].year in (year, year + 1)):
            out.add(h["date"])
    return out


def working_days(start, end, holidays):
    n, d = 0, start
    while d <= end:
        if d.weekday() < 5 and d not in holidays:
            n += 1
        d += dt.timedelta(days=1)
    return n


def _type(t):
    return {"id": t.get_id(), "name": t["name"], "allowance": t["allowance"] or 0, "color": t["color"] or "spruce",
            "paid": t["paid"] is not False, "unlimited": not t["allowance"]}


def types(company):
    return [_type(t) for t in app_tables.leave_types.search(tables.order_by("order"), company=company)]


def balances(e, year=None):
    year = year or C.now().year
    out = []
    reqs = [r for r in app_tables.leave_requests.search(employee=e)
            if r["start"] is not None and r["start"].year == year and r["status"] in ("approved", "pending")]
    for t in app_tables.leave_types.search(tables.order_by("order"), company=e["company"]):
        used = sum(r["days"] or 0 for r in reqs if r["leave_type"] == t and r["status"] == "approved")
        pending = sum(r["days"] or 0 for r in reqs if r["leave_type"] == t and r["status"] == "pending")
        allow = t["allowance"] or 0
        out.append({"type_id": t.get_id(), "name": t["name"], "color": t["color"] or "spruce", "allowance": allow,
                    "used": used, "pending": pending, "left": (allow - used - pending) if allow else None,
                    "unlimited": not allow})
    return out


def _req(r, cx, show_type=True):
    e = r["employee"]
    t = r["leave_type"]
    return {"id": r.get_id(), "person": W.name(e), "person_id": e.get_id() if e is not None else None,
            "initials": W.initials(e), "tone": W.tone(e), "title": e["title"] or "" if e is not None else "",
            "type": (t["name"] if t is not None else "Time off") if show_type else "Time off",
            "color": (t["color"] if t is not None else "slate") if show_type else "slate",
            "start": C.iso(r["start"]), "end": C.iso(r["end"]), "days": r["days"] or 0, "note": r["note"] or "",
            "status": r["status"], "decided_by": r["decided_by_name"] or "", "decision_note": r["decision_note"] or "",
            "created": C.iso(r["created"]), "mine": cx.emp is not None and e == cx.emp,
            "can_decide": can_decide(cx, r), "can_cancel": _can_cancel(cx, r)}


def can_decide(cx, r):
    e = r["employee"]
    if r["status"] != "pending" or e is None or cx.emp is None or e == cx.emp:
        return False
    return cx.is_admin or W.is_above(cx.emp, e)


def _can_cancel(cx, r):
    if r["status"] not in ("pending", "approved"):
        return False
    mine = cx.emp is not None and r["employee"] == cx.emp
    future = r["end"] is not None and r["end"] >= C.now().date()
    return (mine and (r["status"] == "pending" or future)) or (cx.is_admin and future)


def approvals_for(cx):
    rows = app_tables.leave_requests.search(tables.order_by("start"), company=cx.company, status="pending")
    return [r for r in rows if can_decide(cx, r)]


def out_between(cx, start, end):
    rows = app_tables.leave_requests.search(company=cx.company, status=q.any_of("approved", "pending"))
    out = []
    for r in rows:
        if r["start"] is None or r["end"] is None or r["end"] < start or r["start"] > end:
            continue
        if r["employee"] is None or r["employee"]["status"] == "terminated":
            continue
        out.append(_req(r, cx, show_type=W.can_team(cx, r["employee"])))
    return sorted(out, key=lambda x: (x["start"], x["person"]))


@anvil.server.callable(require_user=True)
def timeoff_overview(month=None):
    """My balances and requests, approvals waiting for me, the month's who's-out list, types and holidays."""
    cx = W.ctx()
    today = C.now().date()
    first = _date(month) or today.replace(day=1)
    first = first.replace(day=1)
    nxt = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    mine = app_tables.leave_requests.search(tables.order_by("start", ascending=False), employee=cx.emp)
    hol = [{"id": h.get_id(), "name": h["name"], "date": C.iso(h["date"])}
           for h in app_tables.holidays.search(tables.order_by("date"), company=cx.company)
           if h["date"] is not None and h["date"].year >= today.year - 1]
    return {"balances": balances(cx.emp), "mine": [_req(r, cx) for r in mine[:60]],
            "approvals": [_req(r, cx) for r in approvals_for(cx)], "types": types(cx.company), "holidays": hol,
            "month": first.isoformat(), "out": out_between(cx, first, nxt - dt.timedelta(days=1)),
            "today": today.isoformat(), "is_admin": cx.is_admin, "is_manager": W.is_manager(cx)}


@anvil.server.callable(require_user=True)
def count_days(start, end):
    cx = W.ctx()
    s, e = _date(start), _date(end)
    if s is None or e is None or e < s:
        return 0
    return working_days(s, e, holiday_dates(cx.company))


@anvil.server.callable(require_user=True)
def request_time_off(type_id, start, end, note="", emp_id=None):
    """Ask for time off (HR may enter it for someone else with emp_id)."""
    cx = W.ctx()
    who = cx.emp
    if emp_id and emp_id != (cx.emp.get_id() if cx.emp else None):
        if not cx.is_admin:
            return C.fail("Only HR can add time off for someone else.")
        who = W.emp_in(cx, emp_id)
        if who is None:
            return C.fail("That person isn't in your company.")
    t = W.row_in(cx, app_tables.leave_types, type_id)
    if t is None:
        return C.fail("Choose a type of time off.")
    s, e = _date(start), _date(end)
    if s is None or e is None:
        return C.fail("Choose the first and last day.")
    if e < s:
        return C.fail("The last day is before the first day.")
    if (e - s).days > 370:
        return C.fail("Requests can be up to a year long. Split longer leave into parts.")
    days = working_days(s, e, holiday_dates(cx.company))
    if days == 0:
        return C.fail("Those dates are all weekends or holidays, so there's nothing to take.")
    for r in app_tables.leave_requests.search(employee=who, status=q.any_of("approved", "pending")):
        if r["start"] is not None and r["end"] is not None and not (r["end"] < s or r["start"] > e):
            return C.fail("This overlaps another request (%s to %s)." % (r["start"].isoformat(), r["end"].isoformat()))
    if t["allowance"]:
        bal = next(b for b in balances(who, s.year) if b["type_id"] == t.get_id())
        if days > bal["left"]:
            return C.fail("That's %s, but you have %s of %s left this year." % (
                C_days(days), C_days(bal["left"]), t["name"]))
    if C.rate_limited("request_time_off", 30, 3600):
        return C.fail("That's a lot of requests in one hour. Please try again later.")
    auto = cx.is_admin and who != cx.emp
    r = app_tables.leave_requests.add_row(company=cx.company, employee=who, leave_type=t, start=s, end=e, days=days,
                                          note=C.text(note, 500, True), status="approved" if auto else "pending",
                                          decided_by_name=cx.name if auto else None,
                                          decided_at=C.now() if auto else None, created=C.now(), is_demo=False)
    return C.ok(request=_req(r, cx))


def C_days(n):
    n = n or 0
    return "%g day%s" % (n, "" if n == 1 else "s")


@anvil.server.callable(require_user=True)
def decide_request(req_id, approve, note=""):
    cx = W.ctx()
    r = W.row_in(cx, app_tables.leave_requests, req_id)
    if r is None:
        return C.fail("That request no longer exists.")
    if r["status"] != "pending":
        return C.fail("Someone already answered this request.")
    if not can_decide(cx, r):
        return C.fail("Only %s's manager or HR can answer this request." % W.name(r["employee"]))
    r.update(status="approved" if approve else "declined", decided_by_name=cx.name, decided_at=C.now(),
             decision_note=C.text(note, 500, True))
    return C.ok(request=_req(r, cx))


@anvil.server.callable(require_user=True)
def cancel_request(req_id):
    cx = W.ctx()
    r = W.row_in(cx, app_tables.leave_requests, req_id)
    if r is None:
        return C.ok()
    if not _can_cancel(cx, r):
        return C.fail("This request can't be cancelled any more.")
    r.update(status="cancelled", decided_by_name=cx.name, decided_at=C.now())
    return C.ok(request=_req(r, cx))


# ------------------------------------------------------------------------------------------- settings (HR)
@anvil.server.callable(require_user=True)
def save_leave_type(type_id, name, allowance, paid=True, color="spruce"):
    cx = W.ctx()
    W.require_admin(cx)
    name = C.text(name, 40)
    if len(name) < 2:
        return C.fail("Give the type a name (e.g. Vacation).")
    try:
        allowance = max(0.0, min(365.0, float(allowance or 0)))
    except (TypeError, ValueError):
        return C.fail("The allowance must be a number of days (0 = no limit).")
    color = color if color in COLORS else "spruce"
    if type_id:
        t = W.row_in(cx, app_tables.leave_types, type_id)
        if t is None:
            return C.fail("That type no longer exists.")
        t.update(name=name, allowance=allowance, paid=bool(paid), color=color)
    else:
        n = len(app_tables.leave_types.search(company=cx.company))
        t = app_tables.leave_types.add_row(company=cx.company, name=name, allowance=allowance, paid=bool(paid),
                                           color=color, order=n, is_demo=False)
    return C.ok(type=_type(t), types=types(cx.company))


@anvil.server.callable(require_user=True)
def delete_leave_type(type_id):
    cx = W.ctx()
    W.require_admin(cx)
    t = W.row_in(cx, app_tables.leave_types, type_id)
    if t is None:
        return C.ok(types=types(cx.company))
    if len(app_tables.leave_requests.search(leave_type=t)) > 0:
        return C.fail("People have already used %s, so it can't be deleted. Rename it instead." % t["name"])
    t.delete()
    return C.ok(types=types(cx.company))


@anvil.server.callable(require_user=True)
def save_holiday(name, date):
    cx = W.ctx()
    W.require_admin(cx)
    name, d = C.text(name, 60), _date(date)
    if not name or d is None:
        return C.fail("Give the holiday a name and a date.")
    if app_tables.holidays.get(company=cx.company, date=d) is not None:
        return C.fail("There's already a holiday on %s." % d.isoformat())
    app_tables.holidays.add_row(company=cx.company, name=name, date=d, is_demo=False)
    return C.ok()


@anvil.server.callable(require_user=True)
def delete_holiday(holiday_id):
    cx = W.ctx()
    W.require_admin(cx)
    h = W.row_in(cx, app_tables.holidays, holiday_id)
    if h is not None:
        h.delete()
    return C.ok()
