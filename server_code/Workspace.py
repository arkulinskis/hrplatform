"""The company workspace: who you are inside your company, roles, permissions, "view as", company settings,
invites, the change history and the full data export.

Roles live on the employee row: "admin" (HR), "manager", "employee". A manager is also anyone who has people
reporting to them (anywhere down the chain). Every other server module starts with `cx = W.ctx()`.

Permission rules (one place, used by every module):
  - private fields (personal details, files, equipment, time off, change history): the person and HR admins
  - pay: the person, HR admins and anyone above them in the reporting line
  - job fields, notes, invites, settings: HR admins only
  - "view as": a real HR admin can preview the app as any colleague (reads and acts as them, flagged in the header)
"""
import datetime as dt
import json
import secrets as _secrets
import typing

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C

ROLES = ["admin", "manager", "employee"]
STATUSES = ["onboarding", "active", "leave", "terminated"]
EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contractor", "Intern"]
CURRENCIES = ["CAD", "USD", "EUR", "GBP", "AUD"]
DEFAULT_SETTINGS = {
    "departments": ["Leadership", "People", "Engineering", "Design", "Sales", "Operations"],
    "locations": ["Montréal", "Remote"],
    "values": ["Own it", "Be kind", "Ship it", "Stay curious"],
    "onboarding": [
        {"title": "Send the welcome email and first-day plan", "role": "hr", "day": -5},
        {"title": "Order the laptop and accounts", "role": "it", "day": -5},
        {"title": "Fill in personal details and emergency contact", "role": "employee", "day": 0},
        {"title": "Sign the employee handbook", "role": "employee", "day": 1},
        {"title": "Set up a first-week buddy", "role": "manager", "day": 0},
        {"title": "Agree the 30-60-90 day goals", "role": "manager", "day": 7},
        {"title": "30-day check-in", "role": "manager", "day": 30},
    ],
    "offboarding": [
        {"title": "Confirm the last day and final pay", "role": "hr", "day": -10},
        {"title": "Plan the handover of work", "role": "manager", "day": -7},
        {"title": "Exit interview", "role": "hr", "day": -2},
        {"title": "Collect the laptop and badge", "role": "it", "day": 0},
        {"title": "Turn off accounts and access", "role": "it", "day": 0},
    ],
}
TASK_ROLES = {"hr": "HR", "manager": "Manager", "it": "IT", "employee": "New hire"}


class Ctx:
    """Who is calling: the user, their company, their real employee row and the effective one (view as)."""

    def __init__(self, user, company, me, emp):
        self.user, self.company, self.me, self.emp = user, company, me, emp
        self.viewing_as = emp is not None and me is not None and emp != me
        self.role = (emp["role"] if emp is not None else None) or "employee"
        self.is_admin = self.role == "admin"
        self.real_admin = me is not None and me["role"] == "admin"
        self.name = name(emp) if emp is not None else C.name_of(user)


def ctx(need_company=True):
    user = C.require_user()
    company = user["company"]
    if company is None:
        if need_company:
            raise anvil.server.PermissionDenied("Set up or join a company first.")
        return Ctx(user, None, None, None)
    me = app_tables.employees.get(company=company, user=user)
    if me is None:
        if need_company:
            raise anvil.server.PermissionDenied("Your account isn't linked to anyone in this company.")
        return Ctx(user, company, None, None)
    emp = me
    view = anvil.server.session.get("view_as")
    if view and me["role"] == "admin":
        other = C.row_by_id(app_tables.employees, view)
        if other is not None and other["company"] == company:
            emp = other
    return Ctx(user, company, me, emp)


def require_admin(cx):
    if not cx.is_admin:
        raise anvil.server.PermissionDenied("Only HR admins can do that.")


def emp_in(cx, emp_id):
    """An employee row of the caller's company, or None (ids come from the browser)."""
    e = C.row_by_id(app_tables.employees, emp_id)
    return e if e is not None and e["company"] == cx.company else None


def row_in(cx, table, row_id):
    r = C.row_by_id(table, row_id)
    return r if r is not None and r["company"] == cx.company else None


# ------------------------------------------------------------------------------------------- names + reporting line
def name(e):
    if e is None:
        return ""
    first = e["preferred_name"] or e["first_name"] or ""
    return (first + " " + (e["last_name"] or "")).strip() or (e["work_email"] or "Someone")


def initials(e):
    parts = name(e).split()
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def tone(e):
    """Avatar colour 0-5, stable per person."""
    return sum(ord(ch) for ch in name(e)) % 6


def chain(e):
    """Managers above e, nearest first (guards against loops)."""
    out, seen, m = [], set(), e["manager"] if e is not None else None
    while m is not None and m.get_id() not in seen and len(out) < 30:
        seen.add(m.get_id())
        out.append(m)
        m = m["manager"]
    return out


def is_above(viewer, target):
    return viewer is not None and target is not None and any(m == viewer for m in chain(target))


def active_people(company, include_terminated=False):
    rows = app_tables.employees.search(company=company)
    return [e for e in rows if include_terminated or e["status"] != "terminated"]


def reports_of(company, manager, people=None):
    """Everyone below manager (direct and indirect)."""
    people = people if people is not None else active_people(company)
    return [e for e in people if is_above(manager, e)]


def direct_reports(company, manager):
    return [e for e in app_tables.employees.search(company=company, manager=manager) if e["status"] != "terminated"]


def is_manager(cx):
    return cx.emp is not None and len(app_tables.employees.search(company=cx.company, manager=cx.emp)) > 0


def can_private(cx, e):
    return cx.is_admin or (cx.emp is not None and e == cx.emp)


def can_pay(cx, e):
    return can_private(cx, e) or is_above(cx.emp, e)


def can_team(cx, e):
    """The person, their managers up the line, HR."""
    return can_pay(cx, e)


def admins(company):
    return [e for e in app_tables.employees.search(company=company, role="admin") if e["status"] != "terminated"]


# ------------------------------------------------------------------------------------------- dicts for the browser
def card(e, cx=None):
    if e is None:
        return None
    m = e["manager"]
    return {"id": e.get_id(), "name": name(e), "first": e["preferred_name"] or e["first_name"] or "",
            "initials": initials(e), "tone": tone(e), "title": e["title"] or "", "department": e["department"] or "",
            "location": e["location"] or "", "status": e["status"] or "active", "role": e["role"] or "employee",
            "pronouns": e["pronouns"] or "", "start_date": C.iso(e["start_date"]), "end_date": C.iso(e["end_date"]),
            "manager_id": m.get_id() if m is not None else None, "manager_name": name(m) if m is not None else "",
            "work_email": e["work_email"] or "", "employment_type": e["employment_type"] or "",
            "has_account": e["user"] is not None,
            "is_me": cx is not None and cx.emp is not None and e == cx.emp, "demo": bool(e["is_demo"])}


def full(e, cx):
    d = card(e, cx)
    d["about"] = e["about"] or ""
    d["can_private"] = priv = can_private(cx, e)
    d["can_pay"] = pay = can_pay(cx, e)
    d["can_edit_job"] = cx.is_admin
    d["can_admin"] = cx.is_admin
    d["can_team"] = can_team(cx, e)
    if priv:
        d.update(personal_email=e["personal_email"] or "", phone=e["phone"] or "", birthday=C.iso(e["birthday"]),
                 address=e["address"] or "", emergency=dict(e["emergency"] or {}), first_name=e["first_name"] or "",
                 last_name=e["last_name"] or "", preferred_name=e["preferred_name"] or "")
    else:
        b = e["birthday"]
        d["birthday_day"] = "%s-%02d" % (b.month, b.day) if b else ""  # colleagues see the day, never the year
    if pay:
        d.update(pay_rate=e["pay_rate"], pay_period=e["pay_period"] or "year", pay_currency=e["pay_currency"] or "",
                 pay_effective=C.iso(e["pay_effective"]))
    if cx.is_admin:
        d.update(hr_notes=e["hr_notes"] or "", termination=dict(e["termination"] or {}),
                 invite_pending=bool(e["invite_code"]))
    return d


# ------------------------------------------------------------------------------------------- change history
def log(company, e, kind, field, old, new, by_name, effective=None, demo=False):
    app_tables.changes.add_row(company=company, employee=e, kind=kind, field=field,
                               old="" if old is None else str(old)[:300], new="" if new is None else str(new)[:300],
                               effective=effective or C.now().date(), by_name=by_name, when=C.now(), is_demo=demo)


def change_dict(r):
    return {"id": r.get_id(), "kind": r["kind"], "field": r["field"], "old": r["old"], "new": r["new"],
            "effective": C.iso(r["effective"]), "by": r["by_name"], "when": C.iso(r["when"]),
            "person": name(r["employee"]) if r["employee"] is not None else "",
            "person_id": r["employee"].get_id() if r["employee"] is not None else None}


# ------------------------------------------------------------------------------------------- settings
def settings(company):
    s = dict(DEFAULT_SETTINGS)
    s.update(company["settings"] or {})
    return s


def company_dict(company):
    s = settings(company)
    return {"id": company.get_id(), "name": company["name"], "slug": company["slug"], "country": company["country"] or "",
            "currency": company["currency"] or "CAD", "departments": list(s["departments"]),
            "locations": list(s["locations"]), "values": list(s["values"]), "onboarding": list(s["onboarding"]),
            "offboarding": list(s["offboarding"]), "demo": bool(company["is_demo"])}


def me_extras(user):
    """Added to get_me: the company, the effective role and view-as state (one start-up call)."""
    company = user["company"]
    if company is None:
        return {"company": None, "role": None, "emp_id": None, "viewing_as": None}
    me = app_tables.employees.get(company=company, user=user)
    cx = ctx(need_company=False)
    has_reports = cx.emp is not None and len(app_tables.employees.search(company=company, manager=cx.emp)) > 0
    return {"company": company["name"], "company_slug": company["slug"], "currency": company["currency"] or "CAD",
            "role": cx.role if me is not None else None, "real_role": me["role"] if me is not None else None,
            "is_manager": has_reports or cx.role == "manager",
            "emp_id": cx.emp.get_id() if cx.emp is not None else None,
            "emp_name": cx.name if cx.emp is not None else None,
            "viewing_as": name(cx.emp) if cx.viewing_as else None,
            "has_sample": len(app_tables.employees.search(company=company, is_demo=True)) > 0}


def _slug(text):
    base = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    base = "-".join(p for p in base.split("-") if p)[:40] or "company"
    slug, n = base, 2
    while app_tables.companies.get(slug=slug) is not None:
        slug, n = "%s-%d" % (base, n), n + 1
    return slug


def new_company(name_text, country, currency, owner=None, demo=False):
    return app_tables.companies.add_row(name=name_text, slug=_slug(name_text), owner=owner, country=country,
                                        currency=currency, settings={}, created=C.now(), is_demo=demo)


# ------------------------------------------------------------------------------------------- callables
@anvil.server.callable(require_user=True)
def create_company(name_text, country="Canada", currency="CAD", my_title="", sample=True):
    cx = ctx(need_company=False)
    if cx.company is not None:
        return C.fail("You're already in a company workspace.")
    name_text = C.text(name_text, 80)
    if len(name_text) < 2:
        return C.fail("Give your company a name (at least 2 characters).")
    if C.rate_limited("create_company", 5, 3600):
        return C.fail("That's a lot of companies in one hour. Please try again later.")
    currency = currency if currency in CURRENCIES else "CAD"
    company = new_company(name_text, C.text(country, 60) or "Canada", currency, owner=cx.user)
    full_name = C.name_of(cx.user)
    parts = full_name.split(" ", 1)
    me = app_tables.employees.add_row(
        company=company, user=cx.user, first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
        work_email=cx.user["email"], title=C.text(my_title, 80) or "Head of People", department="People",
        location=settings(company)["locations"][0], employment_type="Full-time", start_date=C.now().date(),
        status="active", role="admin", pay_currency=currency, created=C.now(), is_demo=False)
    cx.user["company"] = company
    from . import Sample
    Sample.defaults(company)
    if sample:
        Sample.seed(company, me)
    log(company, me, "system", "Workspace", "", "Created " + name_text, full_name)
    return C.ok(company=company_dict(company))


@anvil.server.callable(require_user=True)
def join_company(code):
    cx = ctx(need_company=False)
    code = C.text(code, 60)
    if cx.company is not None:
        return C.fail("You're already in a company workspace.")
    if C.rate_limited("join_company", 15, 3600):
        return C.fail("Too many tries. Please wait a while and try again.")
    e = app_tables.employees.get(invite_code=code) if code else None
    if e is None or e["user"] is not None:
        return C.fail("That invite link doesn't work any more. Ask HR for a new one.")
    e.update(user=cx.user, invite_code=None)
    if not e["work_email"]:
        e["work_email"] = cx.user["email"]
    cx.user["company"] = e["company"]
    log(e["company"], e, "system", "Account", "", "Joined with an invite link", name(e))
    return C.ok(company=company_dict(e["company"]))


@anvil.server.callable(require_user=True)
def invite_code(emp_id):
    cx = ctx()
    require_admin(cx)
    e = emp_in(cx, emp_id)
    if e is None:
        return C.fail("That person isn't in your company.")
    if e["user"] is not None:
        return C.fail("%s already has an account." % name(e))
    e["invite_code"] = _secrets.token_urlsafe(12)
    return C.ok(code=e["invite_code"], name=name(e))


@anvil.server.callable(require_user=True)
def view_as(emp_id=None):
    cx = ctx()
    if not cx.real_admin:
        return C.fail("Only HR admins can preview the app as someone else.")
    session = typing.cast(dict, anvil.server.session)
    if not emp_id:
        session["view_as"] = None
        return C.ok(viewing_as=None)
    e = emp_in(cx, emp_id)
    if e is None:
        return C.fail("That person isn't in your company.")
    session["view_as"] = None if e == cx.me else e.get_id()
    return C.ok(viewing_as=None if e == cx.me else name(e))


@anvil.server.callable(require_user=True)
def get_company():
    cx = ctx()
    d = company_dict(cx.company)
    d["people"] = len(active_people(cx.company))
    d["is_admin"] = cx.is_admin
    return d


@anvil.server.callable(require_user=True)
def save_company(name_text, country, currency):
    cx = ctx()
    require_admin(cx)
    name_text = C.text(name_text, 80)
    if len(name_text) < 2:
        return C.fail("Give your company a name (at least 2 characters).")
    cx.company.update(name=name_text, country=C.text(country, 60),
                      currency=currency if currency in CURRENCIES else cx.company["currency"])
    return C.ok(company=company_dict(cx.company))


@anvil.server.callable(require_user=True)
def save_list(kind, items):
    """Departments, locations, values (lists of names) or the onboarding/offboarding templates (lists of tasks)."""
    cx = ctx()
    require_admin(cx)
    if kind not in ("departments", "locations", "values", "onboarding", "offboarding") or not isinstance(items, list):
        return C.fail("That list can't be changed.")
    if kind in ("onboarding", "offboarding"):
        clean = []
        for t in items[:40]:
            if not isinstance(t, dict):
                continue
            title = C.text(t.get("title"), 120)
            role = t.get("role") if t.get("role") in TASK_ROLES else "hr"
            try:
                day = max(-60, min(120, int(t.get("day") or 0)))
            except (TypeError, ValueError):
                day = 0
            if title:
                clean.append({"title": title, "role": role, "day": day})
        value: list = clean
    else:
        value = []
        for x in items[:60]:
            v = C.text(x, 60)
            if v and v not in value:
                value.append(v)
        if not value:
            return C.fail("Keep at least one.")
    s = dict(cx.company["settings"] or {})
    s[kind] = value
    cx.company["settings"] = s
    return C.ok(company=company_dict(cx.company))


@anvil.server.callable(require_user=True)
def audit_log(limit=200):
    cx = ctx()
    require_admin(cx)
    rows = app_tables.changes.search(tables.order_by("when", ascending=False), company=cx.company)
    return {"items": [change_dict(r) for r in rows[:max(1, min(int(limit or 200), 500))]], "total": len(rows)}


@anvil.server.callable(require_user=True)
def remove_sample():
    """Delete every sample row of the caller's company (real people and data stay)."""
    cx = ctx()
    require_admin(cx)
    from . import Sample
    n = Sample.remove(cx.company)
    log(cx.company, cx.me, "system", "Sample data", "", "Removed %d sample rows" % n, name(cx.me))
    return C.ok(removed=n)


EXPORT_TABLES = ["employees", "changes", "leave_types", "holidays", "leave_requests", "jobs", "candidates", "checklists",
                 "tasks", "review_cycles", "reviews", "goals", "kudos", "surveys", "survey_answers", "policies", "acks",
                 "announcements", "assets", "files"]


def _plain(v):
    if isinstance(v, (dt.date, dt.datetime)):
        return C.iso(v)
    if hasattr(v, "get_id"):
        return v.get_id()
    if hasattr(v, "get_bytes"):
        return None  # files: names only (download them from each profile)
    return v


@anvil.server.callable(require_user=True)
def export_company():
    """Everything the company has, as JSON text (no lock-in). The browser saves it as a file."""
    cx = ctx()
    require_admin(cx)
    out: dict = {"company": company_dict(cx.company), "exported": C.iso(C.now()), "tables": {}}
    for t in EXPORT_TABLES:
        rows = []
        for r in getattr(app_tables, t).search(company=cx.company):
            d = {"id": r.get_id()}
            for k, v in dict(r).items():
                if k in ("company", "invite_code", "media"):
                    continue
                d[k] = _plain(v)
            rows.append(d)
        out["tables"][t] = rows
    return C.ok(json=json.dumps(out, indent=1, default=str), name=cx.company["slug"] + "-export.json")
