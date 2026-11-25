"""Company policies (handbook pages people acknowledge, with a record of who and when) and announcements.
Editing a policy that needs acknowledging asks everyone again (older acknowledgements no longer count)."""
import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Workspace as W


def _acked(p, e):
    a = app_tables.acks.get(policy=p, employee=e) if e is not None else None
    return a is not None and (p["updated"] is None or a["when"] >= p["updated"])


def _policy(p, cx, full=False):
    people = W.active_people(cx.company)
    mine = app_tables.acks.get(policy=p, employee=cx.emp) if cx.emp is not None else None
    acked = mine is not None and (p["updated"] is None or mine["when"] >= p["updated"])
    d = {"id": p.get_id(), "title": p["title"], "require_ack": bool(p["require_ack"]), "updated": C.iso(p["updated"]),
         "acked": acked, "acked_at": C.iso(mine["when"]) if acked else None, "words": len((p["body"] or "").split())}
    if cx.is_admin and p["require_ack"]:
        d["ack_count"] = len([e for e in people if _acked(p, e)])
        d["people"] = len(people)
    if full:
        d["body"] = p["body"] or ""
    return d


def to_acknowledge(cx):
    return [_policy(p, cx) for p in app_tables.policies.search(company=cx.company, require_ack=True)
            if not _acked(p, cx.emp)]


def _ann(a):
    au = a["author"]
    return {"id": a.get_id(), "title": a["title"], "body": a["body"] or "", "pinned": bool(a["pinned"]),
            "author": W.name(au), "author_initials": W.initials(au), "author_tone": W.tone(au),
            "created": C.iso(a["created"])}


def announcements(company, limit=20):
    rows = app_tables.announcements.search(tables.order_by("created", ascending=False), company=company)
    rows = sorted(rows[:60], key=lambda a: (not a["pinned"],))  # pinned first, then newest
    return [_ann(a) for a in rows[:limit]]


@anvil.server.callable(require_user=True)
def docs_overview():
    cx = W.ctx()
    pols = app_tables.policies.search(tables.order_by("title"), company=cx.company)
    return {"policies": [_policy(p, cx) for p in pols], "announcements": announcements(cx.company, 30),
            "is_admin": cx.is_admin}


@anvil.server.callable(require_user=True)
def get_policy(policy_id):
    cx = W.ctx()
    p = W.row_in(cx, app_tables.policies, policy_id)
    if p is None:
        return C.fail("That policy no longer exists.")
    d = _policy(p, cx, full=True)
    if cx.is_admin and p["require_ack"]:
        d["status"] = [{"name": W.name(e), "id": e.get_id(), "acked": _acked(p, e)}
                       for e in sorted(W.active_people(cx.company), key=lambda e: W.name(e).lower())]
    return C.ok(policy=d)


@anvil.server.callable(require_user=True)
def save_policy(policy_id, title, body, require_ack=True):
    cx = W.ctx()
    W.require_admin(cx)
    title, body = C.text(title, 120), C.text(body, 30000, True)
    if len(title) < 3 or len(body) < 10:
        return C.fail("A policy needs a title and some text.")
    if policy_id:
        p = W.row_in(cx, app_tables.policies, policy_id)
        if p is None:
            return C.fail("That policy no longer exists.")
        p.update(title=title, body=body, require_ack=bool(require_ack), updated=C.now())
    else:
        p = app_tables.policies.add_row(company=cx.company, title=title, body=body, require_ack=bool(require_ack),
                                        updated=C.now(), is_demo=False)
    return C.ok(policy=_policy(p, cx, full=True))


@anvil.server.callable(require_user=True)
def delete_policy(policy_id):
    cx = W.ctx()
    W.require_admin(cx)
    p = W.row_in(cx, app_tables.policies, policy_id)
    if p is not None:
        for a in app_tables.acks.search(policy=p):
            a.delete()
        p.delete()
    return C.ok()


@anvil.server.callable(require_user=True)
def acknowledge(policy_id):
    cx = W.ctx()
    p = W.row_in(cx, app_tables.policies, policy_id)
    if p is None:
        return C.fail("That policy no longer exists.")
    if cx.viewing_as:
        return C.fail("Acknowledgements are personal, so they can't be given while previewing as someone else.")
    a = app_tables.acks.get(policy=p, employee=cx.emp)
    if a is None:
        app_tables.acks.add_row(company=cx.company, policy=p, employee=cx.emp, when=C.now(), is_demo=False)
    else:
        a["when"] = C.now()
    return C.ok(policy=_policy(p, cx, full=True))


@anvil.server.callable(require_user=True)
def post_announcement(title, body, pinned=False):
    cx = W.ctx()
    W.require_admin(cx)
    title, body = C.text(title, 120), C.text(body, 4000, True)
    if len(title) < 3:
        return C.fail("Give the announcement a title.")
    if C.rate_limited("announce", 20, 3600):
        return C.fail("That's a lot of announcements in one hour.")
    a = app_tables.announcements.add_row(company=cx.company, title=title, body=body, author=cx.emp,
                                         pinned=bool(pinned), created=C.now(), is_demo=False)
    return C.ok(announcement=_ann(a))


@anvil.server.callable(require_user=True)
def delete_announcement(ann_id):
    cx = W.ctx()
    W.require_admin(cx)
    a = W.row_in(cx, app_tables.announcements, ann_id)
    if a is not None:
        a.delete()
    return C.ok()
