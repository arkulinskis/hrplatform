"""The home page in one call: what needs you (one inbox for approvals, reviews, tasks, policies, the pulse survey),
who's out, birthdays and work anniversaries, new joiners, announcements, kudos and (for HR) the key numbers."""
import datetime as dt

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Workspace as W
from . import Leave, Onboard, Perform, Docs


def _d(v):
    """date -> '1 Dec' (dates in the inbox read like the rest of the app)."""
    return "%d %s" % (v.day, v.strftime("%b")) if v else ""


def _next_date(month, day, today):
    try:
        d = dt.date(today.year, month, day)
    except ValueError:  # 29 February
        d = dt.date(today.year, 3, 1)
    if d < today:
        try:
            d = dt.date(today.year + 1, month, day)
        except ValueError:
            d = dt.date(today.year + 1, 3, 1)
    return d


def celebrations(cx, people, today, days=30):
    out = []
    for e in people:
        if e["status"] == "terminated":
            continue
        if e["birthday"] is not None:
            d = _next_date(e["birthday"].month, e["birthday"].day, today)
            if (d - today).days <= days:
                out.append({"kind": "birthday", "date": d.isoformat(), "in": (d - today).days, "person": W.name(e),
                            "person_id": e.get_id(), "initials": W.initials(e), "tone": W.tone(e), "years": 0,
                            "text": "Birthday"})
        s = e["start_date"]
        if s is not None and s < today:
            d = _next_date(s.month, s.day, today)
            years = d.year - s.year
            if years >= 1 and (d - today).days <= days:
                out.append({"kind": "anniversary", "date": d.isoformat(), "in": (d - today).days, "person": W.name(e),
                            "person_id": e.get_id(), "initials": W.initials(e), "tone": W.tone(e), "years": years,
                            "text": "%d year%s at the company" % (years, "" if years == 1 else "s")})
    return sorted(out, key=lambda x: (x["in"], x["person"]))


@anvil.server.callable(require_user=True)
def get_home():
    cx = W.ctx()
    today = C.now().date()
    people = W.active_people(cx.company)
    needs = []
    for r in Leave.approvals_for(cx):
        t = r["leave_type"]
        needs.append({"kind": "approval", "icon": "calendar", "title": "%s asked for %s" % (
            W.name(r["employee"]), Leave.C_days(r["days"])), "sub": "%s · %s to %s" % (
            t["name"] if t is not None else "Time off", _d(r["start"]), _d(r["end"])),
            "href": "#timeoff/approvals", "id": r.get_id()})
    for rv in Perform.reviews_to_write(cx):
        needs.append({"kind": "review", "icon": "star", "title": rv["label"], "sub": "%s · due %s" % (rv["cycle"], _d(dt.date.fromisoformat(rv["due"])) if rv["due"] else "soon"),
                      "href": "#review/" + rv["id"], "id": rv["id"]})
    for t in Onboard.my_tasks(cx, 8):
        needs.append({"kind": "task", "icon": "check", "title": t["title"],
                      "sub": "%s · %s · due %s" % (t["person"], t["role_label"], _d(dt.date.fromisoformat(t["due"])) if t["due"] else "soon"),
                      "href": "#checklist/" + (t["checklist_id"] or ""), "id": t["id"], "overdue": t["overdue"]})
    for p in Docs.to_acknowledge(cx):
        needs.append({"kind": "policy", "icon": "book", "title": "Read and acknowledge: " + p["title"],
                      "sub": "About %d minute%s" % (max(1, p["words"] // 200), "" if p["words"] < 400 else "s"),
                      "href": "#policy/" + p["id"], "id": p["id"]})
    survey = Perform.open_survey_for(cx)
    if survey and not cx.viewing_as:
        needs.append({"kind": "survey", "icon": "smile", "title": "Quick anonymous pulse: one question",
                      "sub": survey["question"], "href": "#performance/pulse", "id": survey["id"]})
    week_end = today + dt.timedelta(days=6)
    out = Leave.out_between(cx, today, week_end)
    joiners = [W.card(e, cx) for e in people if e["start_date"] is not None and
               today - dt.timedelta(days=30) <= e["start_date"] <= today + dt.timedelta(days=30)]
    d = {"me": W.card(cx.emp, cx), "company": cx.company["name"], "needs": needs[:30],
         "out_today": [o for o in out if o["start"] <= today.isoformat() <= o["end"] and o["status"] == "approved"],
         "out_week": out, "celebrations": celebrations(cx, people, today)[:8],
         "joiners": sorted(joiners, key=lambda x: x["start_date"] or "")[:6],
         "announcements": Docs.announcements(cx.company, 4), "kudos": Perform.kudos_feed(cx.company, 4),
         "balances": [b for b in Leave.balances(cx.emp) if not b["unlimited"]][:3],
         "is_admin": cx.is_admin, "viewing_as": cx.viewing_as, "today": today.isoformat()}
    if cx.is_admin:
        d["stats"] = {"headcount": len([e for e in people if e["status"] != "onboarding"]),
                      "starting": len([e for e in people if e["status"] == "onboarding"]),
                      "open_jobs": len(app_tables.jobs.search(company=cx.company, status="open")),
                      "candidates": len([c for c in app_tables.candidates.search(company=cx.company)
                                         if c["stage"] not in ("hired", "rejected")]),
                      "pending": len(app_tables.leave_requests.search(company=cx.company, status="pending")),
                      "on_leave": len([e for e in people if e["status"] == "leave"])}
    return d
