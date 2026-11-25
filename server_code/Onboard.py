"""Onboarding and offboarding checklists made from the company's templates (Settings). Each task belongs to a role:
HR, IT (handled by HR admins), the manager, or the person themselves. Due dates count from the start date
(onboarding) or the last day (offboarding)."""
import datetime as dt

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Workspace as W


def create(company, e, kind, by_name, demo=False):
    tpl = W.settings(company)["onboarding" if kind == "onboarding" else "offboarding"]
    base = (e["start_date"] if kind == "onboarding" else e["end_date"]) or C.now().date()
    title = ("Welcome %s" if kind == "onboarding" else "Goodbye %s") % W.name(e)
    cl = app_tables.checklists.add_row(company=company, employee=e, kind=kind, title=title, created=C.now(),
                                       is_demo=demo)
    for i, t in enumerate(tpl):
        app_tables.tasks.add_row(company=company, checklist=cl, employee=e, title=t["title"], owner_role=t["role"],
                                 due=base + dt.timedelta(days=int(t.get("day") or 0)), order=i, is_demo=demo)
    return cl


def _owner_ok(cx, t):
    """May the caller tick this task? HR admins: all. Managers: manager tasks of their people. The person: theirs."""
    if cx.is_admin:
        return True
    e = t["employee"]
    if t["owner_role"] == "manager":
        return W.is_above(cx.emp, e)
    if t["owner_role"] == "employee":
        return cx.emp is not None and e == cx.emp
    return False


def _task(t, cx):
    return {"id": t.get_id(), "title": t["title"], "role": t["owner_role"],
            "role_label": W.TASK_ROLES.get(t["owner_role"], "HR"), "due": C.iso(t["due"]),
            "done": t["done_at"] is not None, "done_by": t["done_by_name"] or "", "done_at": C.iso(t["done_at"]),
            "person": W.name(t["employee"]), "person_id": t["employee"].get_id() if t["employee"] is not None else None,
            "checklist_id": t["checklist"].get_id() if t["checklist"] is not None else None,
            "overdue": t["done_at"] is None and t["due"] is not None and t["due"] < C.now().date(),
            "can_tick": _owner_ok(cx, t)}


def _summary(cl, cx):
    tasks = app_tables.tasks.search(checklist=cl)
    done = len([t for t in tasks if t["done_at"] is not None])
    e = cl["employee"]
    return {"id": cl.get_id(), "kind": cl["kind"], "title": cl["title"], "person": W.name(e),
            "person_id": e.get_id() if e is not None else None, "initials": W.initials(e), "tone": W.tone(e),
            "title_job": (e["title"] or "") if e is not None else "",
            "date": C.iso(e["start_date"] if cl["kind"] == "onboarding" else e["end_date"]) if e is not None else None,
            "done": done, "total": len(tasks), "complete": len(tasks) > 0 and done == len(tasks),
            "overdue": len([t for t in tasks if t["done_at"] is None and t["due"] is not None
                            and t["due"] < C.now().date()])}


def _visible(cx, cl):
    e = cl["employee"]
    return cx.is_admin or (cx.emp is not None and (e == cx.emp or W.is_above(cx.emp, e)))


def summaries_for(cx, e):
    return [_summary(cl, cx) for cl in app_tables.checklists.search(employee=e) if _visible(cx, cl)]


def my_tasks(cx, limit=50):
    """Open tasks the caller should do (role match)."""
    out = []
    for t in app_tables.tasks.search(tables.order_by("due"), company=cx.company, done_at=None):
        e = t["employee"]
        if e is None or (e["status"] == "terminated" and t["checklist"] is not None and t["checklist"]["kind"] == "onboarding"):
            continue
        role = t["owner_role"]
        if (role in ("hr", "it") and cx.is_admin) or (role == "manager" and e["manager"] == cx.emp) \
                or (role == "employee" and e == cx.emp):
            out.append(_task(t, cx))
        if len(out) >= limit:
            break
    return out


@anvil.server.callable(require_user=True)
def onboarding_overview():
    cx = W.ctx()
    lists = [cl for cl in app_tables.checklists.search(tables.order_by("created", ascending=False), company=cx.company)
             if _visible(cx, cl)]
    sums = [_summary(cl, cx) for cl in lists]
    people = sorted(W.active_people(cx.company), key=lambda p: W.name(p).lower()) if cx.is_admin else []
    return {"open": [s for s in sums if not s["complete"]], "done": [s for s in sums if s["complete"]][:20],
            "my_tasks": my_tasks(cx), "is_admin": cx.is_admin,
            "people": [{"id": p.get_id(), "name": W.name(p)} for p in people], "roles": W.TASK_ROLES}


@anvil.server.callable(require_user=True)
def get_checklist(cl_id):
    cx = W.ctx()
    cl = W.row_in(cx, app_tables.checklists, cl_id)
    if cl is None or not _visible(cx, cl):
        return C.fail("That checklist isn't one you can see.")
    tasks = app_tables.tasks.search(tables.order_by("order"), checklist=cl)
    return C.ok(checklist=_summary(cl, cx), tasks=[_task(t, cx) for t in tasks], can_edit=cx.is_admin,
                roles=W.TASK_ROLES)


@anvil.server.callable(require_user=True)
def tick_task(task_id, done=True):
    cx = W.ctx()
    t = W.row_in(cx, app_tables.tasks, task_id)
    if t is None:
        return C.fail("That task no longer exists.")
    if not _owner_ok(cx, t):
        return C.fail("This task is for %s." % W.TASK_ROLES.get(t["owner_role"], "HR"))
    if done:
        t.update(done_at=C.now(), done_by_name=cx.name)
    else:
        t.update(done_at=None, done_by_name=None)
    return C.ok(task=_task(t, cx))


@anvil.server.callable(require_user=True)
def add_task(cl_id, title, role="hr", due=None):
    cx = W.ctx()
    W.require_admin(cx)
    cl = W.row_in(cx, app_tables.checklists, cl_id)
    title = C.text(title, 120)
    if cl is None:
        return C.fail("That checklist no longer exists.")
    if not title:
        return C.fail("Say what needs doing.")
    try:
        d = dt.date.fromisoformat(str(due)[:10]) if due else C.now().date()
    except ValueError:
        return C.fail("The due date isn't a date.")
    n = len(app_tables.tasks.search(checklist=cl))
    t = app_tables.tasks.add_row(company=cx.company, checklist=cl, employee=cl["employee"], title=title,
                                 owner_role=role if role in W.TASK_ROLES else "hr", due=d, order=n, is_demo=False)
    return C.ok(task=_task(t, cx))


@anvil.server.callable(require_user=True)
def delete_task(task_id):
    cx = W.ctx()
    W.require_admin(cx)
    t = W.row_in(cx, app_tables.tasks, task_id)
    if t is not None:
        t.delete()
    return C.ok()


@anvil.server.callable(require_user=True)
def start_checklist(emp_id, kind):
    cx = W.ctx()
    W.require_admin(cx)
    e = W.emp_in(cx, emp_id)
    if e is None or kind not in ("onboarding", "offboarding"):
        return C.fail("Choose a person.")
    if kind == "offboarding" and e["end_date"] is None:
        return C.fail("Set a last day first (Offboard on their profile).")
    cl = create(cx.company, e, kind, cx.name)
    return C.ok(checklist=_summary(cl, cx))
