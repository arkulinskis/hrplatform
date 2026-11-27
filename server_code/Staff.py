"""People: the directory, profiles (with field-level permissions), edits with change history, adding people, CSV
import, termination, the org chart, employee files and equipment."""
import csv
import datetime as dt
import io

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Workspace as W

MAX_FILE = 8 * 1024 * 1024


def _date(v):
    """'2026-03-01' -> date, '' -> None, bad -> False."""
    if v in (None, ""):
        return None
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return False


def _people_dicts(cx, rows):
    return [W.card(e, cx) for e in sorted(rows, key=lambda e: W.name(e).lower())]


@anvil.server.callable(require_user=True)
def list_people(include_former=False):
    cx = W.ctx()
    rows = W.active_people(cx.company, include_terminated=bool(include_former) and cx.is_admin)
    s = W.settings(cx.company)
    return {"people": _people_dicts(cx, rows), "departments": list(s["departments"]), "locations": list(s["locations"]),
            "can_add": cx.is_admin, "former": len([e for e in app_tables.employees.search(company=cx.company)
                                                  if e["status"] == "terminated"]) if cx.is_admin else 0}


@anvil.server.callable(require_user=True)
def get_person(emp_id):
    cx = W.ctx()
    e = W.emp_in(cx, emp_id)
    if e is None or (e["status"] == "terminated" and not cx.is_admin):
        return C.fail("That person isn't in your company (or has left).")
    from . import Leave, Onboard, Perform
    d = W.full(e, cx)
    m = e["manager"]
    d["manager"] = W.card(m, cx) if m is not None else None
    d["reports"] = _people_dicts(cx, W.direct_reports(cx.company, e))
    d["goals"] = Perform.goals_for(e) if d["can_team"] else []
    d["kudos"] = Perform.kudos_for(cx.company, e)[:6]
    if d["can_private"]:
        d["history"] = [W.change_dict(r) for r in
                        app_tables.changes.search(tables.order_by("when", ascending=False), employee=e)[:80]]
        d["files"] = [_file(f) for f in app_tables.files.search(tables.order_by("created", ascending=False), employee=e)]
        d["assets"] = [_asset(a) for a in app_tables.assets.search(employee=e)]
    else:
        d["history"], d["files"], d["assets"] = [], [], []
    d["balances"] = Leave.balances(e) if d["can_team"] else []
    d["checklists"] = Onboard.summaries_for(cx, e) if d["can_team"] else []
    s = W.settings(cx.company)
    d["options"] = {"departments": list(s["departments"]), "locations": list(s["locations"]),
                    "types": W.EMPLOYMENT_TYPES, "roles": W.ROLES, "statuses": W.STATUSES,
                    "currencies": W.CURRENCIES,
                    "managers": [{"id": p.get_id(), "name": W.name(p)} for p in
                                 sorted(W.active_people(cx.company), key=lambda p: W.name(p).lower()) if p != e]}
    return C.ok(person=d)


PERSONAL = ["first_name", "last_name", "preferred_name", "pronouns", "personal_email", "phone", "birthday", "address",
            "about"]
JOB = ["title", "department", "location", "manager", "employment_type", "start_date", "role", "work_email"]
PAY = ["pay_rate", "pay_period", "pay_currency"]
LABELS = {"first_name": "First name", "last_name": "Last name", "preferred_name": "Preferred name",
          "pronouns": "Pronouns", "personal_email": "Personal email", "phone": "Phone", "birthday": "Birthday",
          "address": "Address", "about": "About", "title": "Job title", "department": "Department",
          "location": "Location", "manager": "Manager", "employment_type": "Employment type",
          "start_date": "Start date", "role": "Access", "work_email": "Work email", "pay_rate": "Pay rate",
          "pay_period": "Pay period", "pay_currency": "Currency", "emergency": "Emergency contact",
          "hr_notes": "HR notes", "status": "Status"}


def _clean(cx, e, field, value):
    """(value to store, display text) or raises ValueError with a message."""
    if field in ("birthday", "start_date"):
        d = _date(value)
        if d is False:
            raise ValueError("%s isn't a date." % LABELS[field])
        if field == "start_date" and d is None:
            raise ValueError("A start date is needed.")
        return d, C.iso(d) or ""
    if field == "manager":
        if not value:
            return None, "(none)"
        m = W.emp_in(cx, value)
        if m is None:
            raise ValueError("That manager isn't in your company.")
        if m == e or W.is_above(e, m):
            raise ValueError("Someone can't report to themselves or to their own report.")
        return m, W.name(m)
    if field == "pay_rate":
        if value in (None, ""):
            return None, ""
        try:
            n = round(float(value), 2)
        except (TypeError, ValueError):
            raise ValueError("Pay rate must be a number.")
        if n < 0 or n > 100000000:
            raise ValueError("That pay rate looks wrong.")
        return n, "%g" % n
    if field == "pay_period":
        v = value if value in ("year", "hour", "month") else "year"
        return v, v
    if field == "pay_currency":
        v = value if value in W.CURRENCIES else (cx.company["currency"] or "CAD")
        return v, v
    if field == "employment_type":
        v = value if value in W.EMPLOYMENT_TYPES else "Full-time"
        return v, v
    if field == "role":
        v = value if value in W.ROLES else "employee"
        return v, v
    limit = 2000 if field in ("about", "address") else 120
    v = C.text(value, limit, multiline=field in ("about", "address"))
    if field == "first_name" and not v:
        raise ValueError("A first name is needed.")
    if field in ("personal_email", "work_email") and v and "@" not in v:
        raise ValueError("That email address doesn't look right.")
    return v, v


@anvil.server.callable(require_user=True)
def update_person(emp_id, section, data, effective=None):
    """section: personal (the person or HR), job / pay / notes (HR; pay also needs an effective date)."""
    cx = W.ctx()
    e = W.emp_in(cx, emp_id)
    if e is None or not isinstance(data, dict):
        return C.fail("That person isn't in your company.")
    if section == "personal":
        if not W.can_private(cx, e):
            return C.fail("Only %s and HR can change these details." % W.name(e))
        fields = PERSONAL
    elif section in ("job", "pay", "notes"):
        if not cx.is_admin:
            return C.fail("Only HR admins can change job and pay details.")
        fields = {"job": JOB, "pay": PAY, "notes": ["hr_notes"]}[section]
    else:
        return C.fail("Unknown section.")
    eff = _date(effective) if effective else C.now().date()
    if eff is False or eff is None:
        return C.fail("The effective date isn't a date.")
    changes: dict = {}
    shown = []
    try:
        for f in fields:
            if f not in data:
                continue
            if f == "hr_notes":
                v, txt = C.text(data[f], 5000, multiline=True), "(updated)"
            else:
                v, txt = _clean(cx, e, f, data[f])
            old = e[f]
            if old != v:
                changes[f] = v
                old_txt = W.name(old) if f == "manager" and old is not None else (C.iso(old) if old is not None else "")
                shown.append((f, old_txt if f != "hr_notes" else "", txt))
    except ValueError as err:
        return C.fail(str(err))
    if section == "personal" and isinstance(data.get("emergency"), dict):
        em = {k: C.text(data["emergency"].get(k), 120) for k in ("name", "relation", "phone")}
        if em != dict(e["emergency"] or {}):
            changes["emergency"] = em
            shown.append(("emergency", "", " · ".join(x for x in em.values() if x)))
    if section == "job" and "role" in changes and e == cx.me and changes["role"] != "admin":
        return C.fail("You can't remove your own HR admin access.")
    if section == "pay" and changes:
        changes["pay_effective"] = eff
    if not changes:
        return C.ok(person=W.full(e, cx), changed=0)
    e.update(**changes)
    kind = {"personal": "personal", "job": "job", "pay": "pay", "notes": "notes"}[section]
    for f, old_txt, txt in shown:
        W.log(cx.company, e, kind, LABELS.get(f, f), old_txt, txt, cx.name, effective=eff)
    return C.ok(person=W.full(e, cx), changed=len(shown))


def _new_person(cx, data, demo=False):
    first = C.text(data.get("first_name"), 60)
    if not first:
        raise ValueError("A first name is needed.")
    start = _date(data.get("start_date")) or C.now().date()
    if start is False:
        raise ValueError("The start date isn't a date.")
    s = W.settings(cx.company)
    manager = W.emp_in(cx, data.get("manager")) if data.get("manager") else None
    email = C.text(data.get("work_email"), 120)
    if email and "@" not in email:
        raise ValueError("That email address doesn't look right.")
    if email and app_tables.employees.get(company=cx.company, work_email=email) is not None:
        raise ValueError("Someone in your company already has the email %s." % email)
    rate = data.get("pay_rate")
    try:
        rate = round(float(rate), 2) if rate not in (None, "") else None
    except (TypeError, ValueError):
        raise ValueError("Pay rate must be a number.")
    e = app_tables.employees.add_row(
        company=cx.company, first_name=first, last_name=C.text(data.get("last_name"), 60),
        work_email=email, title=C.text(data.get("title"), 80),
        department=C.text(data.get("department"), 60) or s["departments"][0],
        location=C.text(data.get("location"), 60) or s["locations"][0], manager=manager,
        employment_type=data.get("employment_type") if data.get("employment_type") in W.EMPLOYMENT_TYPES else "Full-time",
        start_date=start, status="onboarding" if start > C.now().date() else "active",
        role=data.get("role") if data.get("role") in W.ROLES else "employee",
        pay_rate=rate, pay_period=data.get("pay_period") if data.get("pay_period") in ("year", "hour", "month") else "year",
        pay_currency=cx.company["currency"] or "CAD", pay_effective=start if rate is not None else None,
        birthday=_date(data.get("birthday")) or None, created=C.now(), is_demo=demo)
    W.log(cx.company, e, "status", "Status", "", "Hired as %s" % (e["title"] or "team member"), cx.name, effective=start)
    return e


@anvil.server.callable(require_user=True)
def add_person(data, onboarding=True):
    cx = W.ctx()
    W.require_admin(cx)
    if not isinstance(data, dict):
        return C.fail("Nothing to add.")
    if not W.seats_ok(cx, 1):
        return {"ok": False, "error": W.SEATS_MESSAGE, "plan": True}
    try:
        e = _new_person(cx, data)
    except ValueError as err:
        return C.fail(str(err))
    if onboarding:
        from . import Onboard
        Onboard.create(cx.company, e, "onboarding", cx.name)
    return C.ok(person=W.card(e, cx))


IMPORT_COLUMNS = {
    "first name": "first_name", "first": "first_name", "given name": "first_name",
    "last name": "last_name", "last": "last_name", "surname": "last_name", "family name": "last_name",
    "email": "work_email", "work email": "work_email", "title": "title", "job title": "title",
    "department": "department", "team": "department", "location": "location", "office": "location",
    "manager email": "manager_email", "manager": "manager_email", "start date": "start_date", "hire date": "start_date",
    "employment type": "employment_type", "type": "employment_type", "birthday": "birthday", "date of birth": "birthday",
    "pay rate": "pay_rate", "salary": "pay_rate", "name": "full_name", "full name": "full_name",
}


@anvil.server.callable(require_user=True)
def import_people(csv_text, commit=False):
    """Paste a spreadsheet as CSV. Headers are matched by name; returns a preview (rows + problems), or adds them."""
    cx = W.ctx()
    W.require_admin(cx)
    text = (csv_text or "").strip()
    if not text:
        return C.fail("Paste the CSV text first (with a header row).")
    if len(text) > 400000:
        return C.fail("That's too much at once. Import up to about 1,000 people per paste.")
    sample = text[:2000]
    delim = "\t" if sample.count("\t") > sample.count(",") else (";" if sample.count(";") > sample.count(",") else ",")
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if len(rows) < 2:
        return C.fail("Add a header row and at least one person.")
    header = [IMPORT_COLUMNS.get(h.strip().lower().replace("_", " ")) for h in rows[0]]
    if "first_name" not in header and "full_name" not in header:
        return C.fail("No 'First name' (or 'Name') column found. Headers found: %s" % ", ".join(rows[0][:12]))
    existing = {(e["work_email"] or "").lower() for e in app_tables.employees.search(company=cx.company)}
    seen = set()
    preview, problems = [], 0
    for i, r in enumerate(rows[1:1001], start=2):
        d = {k: (r[j].strip() if j < len(r) else "") for j, k in enumerate(header) if k}
        if d.get("full_name") and not d.get("first_name"):
            parts = d["full_name"].split(" ", 1)
            d["first_name"], d["last_name"] = parts[0], parts[1] if len(parts) > 1 else ""
        issues = []
        if not d.get("first_name"):
            issues.append("no first name")
        mail = d.get("work_email", "").lower()
        if mail and "@" not in mail:
            issues.append("bad email")
        if mail and (mail in existing or mail in seen):
            issues.append("email already in use")
        seen.add(mail)
        for f in ("start_date", "birthday"):
            if d.get(f) and _date(d[f]) is False:
                issues.append("%s not YYYY-MM-DD" % f.replace("_", " "))
        problems += 1 if issues else 0
        preview.append({"line": i, "name": (d.get("first_name", "") + " " + d.get("last_name", "")).strip(),
                        "email": d.get("work_email", ""), "title": d.get("title", ""),
                        "department": d.get("department", ""), "issues": ", ".join(issues), "data": d})
    if not commit:
        return C.ok(rows=[{k: v for k, v in p.items() if k != "data"} for p in preview], problems=problems,
                    total=len(preview), mapped=[h for h in header if h])
    if not W.seats_ok(cx, len([p for p in preview if not p["issues"]])):
        return {"ok": False, "error": W.SEATS_MESSAGE, "plan": True}
    added, by_mail = [], {}
    for p in preview:
        if p["issues"]:
            continue
        try:
            e = _new_person(cx, p["data"])
        except ValueError:
            continue
        added.append((e, p["data"].get("manager_email", "").lower()))
        if e["work_email"]:
            by_mail[e["work_email"].lower()] = e
    for e in app_tables.employees.search(company=cx.company):
        if e["work_email"]:
            by_mail.setdefault(e["work_email"].lower(), e)
    for e, m in added:
        if m and m in by_mail and by_mail[m] != e:
            e["manager"] = by_mail[m]
    return C.ok(added=len(added), skipped=len(preview) - len(added))


@anvil.server.callable(require_user=True)
def terminate(emp_id, data):
    """End someone's employment: last day, reason, regretted, rehire; starts the offboarding checklist."""
    cx = W.ctx()
    W.require_admin(cx)
    e = W.emp_in(cx, emp_id)
    if e is None or not isinstance(data, dict):
        return C.fail("That person isn't in your company.")
    if e == cx.me:
        return C.fail("You can't offboard yourself.")
    last = _date(data.get("end_date"))
    if not last:
        return C.fail("Choose the last working day.")
    reason = C.text(data.get("reason"), 60) or "Resignation"
    e.update(end_date=last, termination={"reason": reason, "regretted": bool(data.get("regretted")),
                                         "rehire": bool(data.get("rehire", True)), "note": C.text(data.get("note"), 1000, True)},
             status="terminated" if last <= C.now().date() else e["status"])
    for r in W.direct_reports(cx.company, e):
        r["manager"] = e["manager"]
    W.log(cx.company, e, "status", "Status", "", "Leaving: %s (last day %s)" % (reason, last.isoformat()), cx.name,
          effective=last)
    from . import Onboard
    Onboard.create(cx.company, e, "offboarding", cx.name)
    return C.ok(person=W.full(e, cx))


@anvil.server.callable(require_user=True)
def set_status(emp_id, status):
    cx = W.ctx()
    W.require_admin(cx)
    e = W.emp_in(cx, emp_id)
    if e is None or status not in W.STATUSES:
        return C.fail("Can't set that status.")
    if status == "terminated":
        return C.fail("Use Offboard to end someone's employment.")
    old = e["status"]
    if old == "terminated" and not e["is_demo"] and not W.seats_ok(cx, 1):   # rehiring takes a seat again
        return {"ok": False, "error": W.SEATS_MESSAGE, "plan": True}
    if old != status:
        e["status"] = status
        if old == "terminated":
            e.update(end_date=None, termination=None)
        W.log(cx.company, e, "status", "Status", old, status, cx.name)
    return C.ok(person=W.full(e, cx))


@anvil.server.callable(require_user=True)
def org_chart():
    cx = W.ctx()
    people = W.active_people(cx.company)
    nodes = []
    for e in people:
        m = e["manager"]
        nodes.append({"id": e.get_id(), "name": W.name(e), "title": e["title"] or "", "department": e["department"] or "",
                      "initials": W.initials(e), "tone": W.tone(e), "status": e["status"],
                      "manager_id": m.get_id() if m is not None and m["status"] != "terminated" else None,
                      "me": cx.emp is not None and e == cx.emp})
    open_roles = [{"title": j["title"], "department": j["department"] or "",
                   "manager_id": j["hiring_manager"].get_id() if j["hiring_manager"] is not None else None}
                  for j in app_tables.jobs.search(company=cx.company, status="open")]
    return {"nodes": nodes, "open_roles": open_roles, "company": cx.company["name"]}


# ------------------------------------------------------------------------------------------- files
def _file(f):
    return {"id": f.get_id(), "name": f["name"], "size": f["size"] or 0, "by": f["by_name"] or "",
            "created": C.iso(f["created"])}


@anvil.server.callable(require_user=True)
def upload_file(emp_id, media):
    cx = W.ctx()
    e = W.emp_in(cx, emp_id)
    if e is None or not W.can_private(cx, e):
        return C.fail("Only %s and HR can add files here." % (W.name(e) if e else "the person"))
    if media is None:
        return C.fail("Choose a file first.")
    size = len(media.get_bytes())
    if size > MAX_FILE:
        return C.fail("Files can be up to 8 MB.")
    if C.rate_limited("upload_file", 40, 3600):
        return C.fail("That's a lot of uploads in one hour. Please try again later.")
    f = app_tables.files.add_row(company=cx.company, employee=e, name=C.text(media.name or "file", 120), media=media,
                                 size=size, by_name=cx.name, created=C.now(), is_demo=False)
    W.log(cx.company, e, "personal", "File", "", "Added " + f["name"], cx.name)
    return C.ok(file=_file(f))


@anvil.server.callable(require_user=True)
def get_file(file_id):
    cx = W.ctx()
    f = W.row_in(cx, app_tables.files, file_id)
    if f is None or not W.can_private(cx, f["employee"]):
        return None
    return f["media"]


@anvil.server.callable(require_user=True)
def delete_file(file_id):
    cx = W.ctx()
    f = W.row_in(cx, app_tables.files, file_id)
    if f is None:
        return C.ok()
    if not W.can_private(cx, f["employee"]):
        return C.fail("Only the person and HR can delete their files.")
    W.log(cx.company, f["employee"], "personal", "File", f["name"], "(deleted)", cx.name)
    f.delete()
    return C.ok()


# ------------------------------------------------------------------------------------------- equipment
def _asset(a):
    e = a["employee"]
    return {"id": a.get_id(), "kind": a["kind"] or "Other", "name": a["name"] or "", "serial": a["serial"] or "",
            "assigned": C.iso(a["assigned"]), "returned": C.iso(a["returned"]),
            "person": W.name(e) if e is not None else "", "person_id": e.get_id() if e is not None else None}


ASSET_KINDS = ["Laptop", "Phone", "Monitor", "Badge", "Headset", "Vehicle", "Other"]


@anvil.server.callable(require_user=True)
def save_asset(emp_id, data):
    cx = W.ctx()
    W.require_admin(cx)
    e = W.emp_in(cx, emp_id)
    if e is None or not isinstance(data, dict):
        return C.fail("That person isn't in your company.")
    item = C.text(data.get("name"), 80)
    if not item:
        return C.fail("Say what the item is (e.g. MacBook Air 13).")
    a = app_tables.assets.add_row(company=cx.company, employee=e,
                                  kind=data.get("kind") if data.get("kind") in ASSET_KINDS else "Other", name=item,
                                  serial=C.text(data.get("serial"), 60), assigned=C.now().date(), is_demo=False)
    W.log(cx.company, e, "personal", "Equipment", "", "Given " + item, cx.name)
    return C.ok(asset=_asset(a))


@anvil.server.callable(require_user=True)
def return_asset(asset_id):
    cx = W.ctx()
    W.require_admin(cx)
    a = W.row_in(cx, app_tables.assets, asset_id)
    if a is None:
        return C.fail("That item isn't in your company.")
    if a["returned"] is None:
        a["returned"] = C.now().date()
        if a["employee"] is not None:
            W.log(cx.company, a["employee"], "personal", "Equipment", a["name"], "Returned", cx.name)
    return C.ok(asset=_asset(a))
