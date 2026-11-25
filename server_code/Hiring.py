"""Hiring: job openings, the candidate pipeline (stages), ratings and notes, one-click hire (creates the employee
and their onboarding checklist), and the public careers page with its application form.

Who sees what: HR admins see every job; a hiring manager sees their own jobs; everyone can see open roles
(to refer people). Candidates' details are only for HR and the job's hiring manager."""
import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Workspace as W

STAGES = ["applied", "screen", "interview", "offer", "hired", "rejected"]
STAGE_LABELS = {"applied": "Applied", "screen": "Phone screen", "interview": "Interview", "offer": "Offer",
                "hired": "Hired", "rejected": "Not moving on"}
SOURCES = ["Careers page", "Referral", "LinkedIn", "Job board", "Agency", "Other"]


def _can_job(cx, j):
    return cx.is_admin or (cx.emp is not None and j["hiring_manager"] == cx.emp)


def _job(j, cx, with_counts=True):
    m = j["hiring_manager"]
    d = {"id": j.get_id(), "title": j["title"], "department": j["department"] or "", "location": j["location"] or "",
         "employment_type": j["employment_type"] or "Full-time", "description": j["description"] or "",
         "status": j["status"] or "draft", "salary_range": j["salary_range"] or "",
         "manager": W.name(m) if m is not None else "", "manager_id": m.get_id() if m is not None else None,
         "created": C.iso(j["created"]), "can_manage": _can_job(cx, j) if cx is not None else False}
    if with_counts:
        cands = app_tables.candidates.search(job=j)
        d["counts"] = {s: len([c for c in cands if c["stage"] == s]) for s in STAGES}
        d["active"] = len([c for c in cands if c["stage"] not in ("hired", "rejected")])
        d["total"] = len(cands)
    return d


def _cand(c, full=False):
    d = {"id": c.get_id(), "name": c["name"], "email": c["email"] or "", "stage": c["stage"],
         "stage_label": STAGE_LABELS.get(c["stage"], c["stage"]), "rating": c["rating"] or 0,
         "source": c["source"] or "", "created": C.iso(c["created"]), "notes_count": len(c["notes"] or []),
         "initials": "".join(p[0] for p in (c["name"] or "?").split()[:2]).upper(),
         "tone": sum(ord(ch) for ch in c["name"] or "") % 6, "job": c["job"]["title"] if c["job"] is not None else "",
         "job_id": c["job"].get_id() if c["job"] is not None else None,
         "employee_id": c["employee"].get_id() if c["employee"] is not None else None}
    if full:
        d.update(phone=c["phone"] or "", link=c["link"] or "", cover=c["cover"] or "",
                 notes=list(reversed(list(c["notes"] or []))))
    return d


@anvil.server.callable(require_user=True)
def hiring_overview():
    cx = W.ctx()
    jobs = app_tables.jobs.search(tables.order_by("created", ascending=False), company=cx.company)
    mine = [j for j in jobs if _can_job(cx, j)]
    open_roles = [_job(j, cx, with_counts=False) for j in jobs if j["status"] == "open" and not _can_job(cx, j)]
    recent = []
    if cx.is_admin:
        cands = app_tables.candidates.search(tables.order_by("created", ascending=False), company=cx.company)
        recent = [_cand(c) for c in cands[:8] if c["stage"] == "applied"]
    s = W.settings(cx.company)
    return {"jobs": [_job(j, cx) for j in mine], "open_roles": open_roles, "recent": recent,
            "can_create": cx.is_admin, "slug": cx.company["slug"], "stages": STAGES, "stage_labels": STAGE_LABELS,
            "departments": list(s["departments"]), "locations": list(s["locations"]),
            "managers": [{"id": p.get_id(), "name": W.name(p)} for p in
                         sorted(W.active_people(cx.company), key=lambda p: W.name(p).lower())]}


@anvil.server.callable(require_user=True)
def get_job(job_id):
    cx = W.ctx()
    j = W.row_in(cx, app_tables.jobs, job_id)
    if j is None:
        return C.fail("That job no longer exists.")
    if not _can_job(cx, j):
        return C.fail("Only HR and the hiring manager can see the candidates for this job.")
    cands = app_tables.candidates.search(tables.order_by("created", ascending=False), job=j)
    columns = [{"stage": s, "label": STAGE_LABELS[s], "candidates": [_cand(c) for c in cands if c["stage"] == s]}
               for s in STAGES]
    return C.ok(job=_job(j, cx), columns=columns, sources=SOURCES)


@anvil.server.callable(require_user=True)
def save_job(job_id, data):
    cx = W.ctx()
    W.require_admin(cx)
    if not isinstance(data, dict):
        return C.fail("Nothing to save.")
    title = C.text(data.get("title"), 80)
    if len(title) < 2:
        return C.fail("Give the job a title.")
    m = W.emp_in(cx, data.get("manager_id")) if data.get("manager_id") else None
    vals: dict = dict(title=title, department=C.text(data.get("department"), 60), location=C.text(data.get("location"), 60),
                employment_type=data.get("employment_type") if data.get("employment_type") in W.EMPLOYMENT_TYPES
                else "Full-time", description=C.text(data.get("description"), 8000, True),
                salary_range=C.text(data.get("salary_range"), 60), hiring_manager=m,
                status=data.get("status") if data.get("status") in ("draft", "open", "closed") else "open")
    if job_id:
        j = W.row_in(cx, app_tables.jobs, job_id)
        if j is None:
            return C.fail("That job no longer exists.")
        j.update(**vals)
    else:
        j = app_tables.jobs.add_row(company=cx.company, created=C.now(), is_demo=False, **vals)
    return C.ok(job=_job(j, cx))


def _cand_in(cx, cand_id):
    c = W.row_in(cx, app_tables.candidates, cand_id)
    if c is None or c["job"] is None or not _can_job(cx, c["job"]):
        return None
    return c


@anvil.server.callable(require_user=True)
def get_candidate(cand_id):
    cx = W.ctx()
    c = _cand_in(cx, cand_id)
    if c is None:
        return C.fail("That candidate isn't one of your jobs'.")
    return C.ok(candidate=_cand(c, full=True), stages=STAGES, stage_labels=STAGE_LABELS)


@anvil.server.callable(require_user=True)
def add_candidate(job_id, data):
    cx = W.ctx()
    j = W.row_in(cx, app_tables.jobs, job_id)
    if j is None or not _can_job(cx, j) or not isinstance(data, dict):
        return C.fail("Only HR and the hiring manager can add candidates to this job.")
    name = C.text(data.get("name"), 80)
    if len(name) < 2:
        return C.fail("Add the candidate's name.")
    c = app_tables.candidates.add_row(company=cx.company, job=j, name=name, email=C.text(data.get("email"), 120),
                                      phone=C.text(data.get("phone"), 40), link=C.text(data.get("link"), 300),
                                      cover=C.text(data.get("cover"), 4000, True), stage="applied", rating=0,
                                      source=data.get("source") if data.get("source") in SOURCES else "Other",
                                      notes=[], created=C.now(), is_demo=False)
    return C.ok(candidate=_cand(c))


@anvil.server.callable(require_user=True)
def move_candidate(cand_id, stage):
    cx = W.ctx()
    c = _cand_in(cx, cand_id)
    if c is None or stage not in STAGES:
        return C.fail("Can't move that candidate.")
    if stage == "hired" and c["employee"] is None:
        return C.fail("Use Hire to move someone to Hired (it creates their profile).")
    if c["stage"] == "hired" and stage != "hired":
        return C.fail("%s is already hired." % c["name"])
    if c["stage"] != stage:
        notes = list(c["notes"] or [])
        notes.append({"by": cx.name, "text": "Moved to %s" % STAGE_LABELS[stage], "when": C.iso(C.now()), "system": True})
        c.update(stage=stage, notes=notes)
    return C.ok(candidate=_cand(c))


@anvil.server.callable(require_user=True)
def rate_candidate(cand_id, rating):
    cx = W.ctx()
    c = _cand_in(cx, cand_id)
    if c is None:
        return C.fail("Can't rate that candidate.")
    try:
        c["rating"] = max(0, min(5, int(rating)))
    except (TypeError, ValueError):
        return C.fail("Ratings go from 1 to 5.")
    return C.ok(candidate=_cand(c))


@anvil.server.callable(require_user=True)
def add_note(cand_id, text):
    cx = W.ctx()
    c = _cand_in(cx, cand_id)
    text = C.text(text, 2000, True)
    if c is None:
        return C.fail("Can't add a note to that candidate.")
    if not text:
        return C.fail("Write the note first.")
    notes = list(c["notes"] or [])
    notes.append({"by": cx.name, "text": text, "when": C.iso(C.now())})
    c["notes"] = notes[-100:]
    return C.ok(candidate=_cand(c, full=True))


@anvil.server.callable(require_user=True)
def hire_candidate(cand_id, start_date, title=""):
    """Hired: creates the employee (status onboarding), links them, starts their onboarding checklist."""
    cx = W.ctx()
    W.require_admin(cx)
    c = _cand_in(cx, cand_id)
    if c is None:
        return C.fail("That candidate isn't in your company.")
    if c["employee"] is not None:
        return C.fail("%s is already hired." % c["name"])
    from . import Onboard, Staff
    j = c["job"]
    parts = (c["name"] or "").split(" ", 1)
    try:
        e = Staff._new_person(cx, {"first_name": parts[0], "last_name": parts[1] if len(parts) > 1 else "",
                                   "work_email": "", "title": C.text(title, 80) or j["title"],
                                   "department": j["department"], "location": j["location"],
                                   "employment_type": j["employment_type"], "start_date": start_date,
                                   "manager": j["hiring_manager"].get_id() if j["hiring_manager"] is not None else None})
    except ValueError as err:
        return C.fail(str(err))
    if c["email"]:
        e["personal_email"] = c["email"]
    notes = list(c["notes"] or [])
    notes.append({"by": cx.name, "text": "Hired, starting %s" % C.iso(e["start_date"]), "when": C.iso(C.now()),
                  "system": True})
    c.update(stage="hired", employee=e, notes=notes)
    Onboard.create(cx.company, e, "onboarding", cx.name)
    return C.ok(candidate=_cand(c), employee=W.card(e, cx))


# ------------------------------------------------------------------------------------------- public careers page
@anvil.server.callable
def careers_page(slug):
    from . import DemoData
    DemoData.ensure_loaded()
    company = app_tables.companies.get(slug=C.text(slug, 60)) if slug else None
    if company is None:
        return C.fail("We couldn't find that careers page.")
    jobs = app_tables.jobs.search(tables.order_by("created", ascending=False), company=company, status="open")
    return C.ok(company=company["name"], slug=company["slug"], demo=bool(company["is_demo"]),
                jobs=[_job(j, None, with_counts=False) for j in jobs])


@anvil.server.callable
def apply_to_job(job_id, data):
    """A public application. Spam guards: hidden field, time on page, per-session cap; silent success for bots."""
    j = C.row_by_id(app_tables.jobs, job_id)
    if j is None or j["status"] != "open" or not isinstance(data, dict):
        return C.fail("This job isn't open any more.")
    if data.get("website") or (data.get("ms") or 0) < 2500:
        return C.ok()  # bots: pretend it worked
    name, email = C.text(data.get("name"), 80), C.text(data.get("email"), 120)
    if len(name) < 2 or "@" not in email:
        return C.fail("Add your name and an email address we can reach you at.")
    if C.rate_limited("apply", 6, 3600):
        return C.fail("You've sent several applications already. Please try again later.")
    for c in app_tables.candidates.search(job=j, email=email):
        return C.ok()  # already applied: no duplicate
    app_tables.candidates.add_row(company=j["company"], job=j, name=name, email=email,
                                  phone=C.text(data.get("phone"), 40), link=C.text(data.get("link"), 300),
                                  cover=C.text(data.get("cover"), 4000, True), stage="applied", rating=0,
                                  source="Careers page", notes=[], created=C.now(), is_demo=False)
    return C.ok()
