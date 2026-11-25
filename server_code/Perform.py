"""Performance and engagement: review cycles (self + manager reviews), goals, kudos tied to company values, and
anonymous eNPS pulse surveys.

Reviews: the reviewer writes; HR sees everything; the person sees their manager's review once the cycle is closed.
Pulse answers are stored WITHOUT who gave them (a separate table only records that someone answered), and results
show only once at least MIN_ANSWERS people answered."""
import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Workspace as W

MIN_ANSWERS = 3
DEFAULT_QUESTIONS = [
    "What went well this period? Give one or two examples.",
    "What could have gone better, and what would you do differently?",
    "What should the next period focus on?",
]
GOAL_STATUSES = ["on_track", "at_risk", "off_track", "done"]


# ------------------------------------------------------------------------------------------- goals
def _goal(g):
    e = g["employee"]
    return {"id": g.get_id(), "title": g["title"], "progress": int(g["progress"] or 0), "status": g["status"] or "on_track",
            "due": C.iso(g["due"]), "person": W.name(e), "person_id": e.get_id() if e is not None else None,
            "initials": W.initials(e), "tone": W.tone(e)}


def goals_for(e):
    return [_goal(g) for g in app_tables.goals.search(tables.order_by("created", ascending=False), employee=e)]


@anvil.server.callable(require_user=True)
def save_goal(goal_id, emp_id, title, due=None, progress=0, status="on_track"):
    cx = W.ctx()
    import datetime as dt
    title = C.text(title, 160)
    if len(title) < 3:
        return C.fail("Describe the goal in a few words.")
    try:
        progress = max(0, min(100, int(progress or 0)))
    except (TypeError, ValueError):
        return C.fail("Progress is a percentage from 0 to 100.")
    try:
        d = dt.date.fromisoformat(str(due)[:10]) if due else None
    except ValueError:
        return C.fail("The due date isn't a date.")
    status = status if status in GOAL_STATUSES else "on_track"
    if progress == 100:
        status = "done"
    if goal_id:
        g = W.row_in(cx, app_tables.goals, goal_id)
        if g is None or not W.can_team(cx, g["employee"]):
            return C.fail("Only the person, their manager and HR can change this goal.")
        g.update(title=title, due=d, progress=progress, status=status)
    else:
        e = W.emp_in(cx, emp_id) if emp_id else cx.emp
        if e is None or not W.can_team(cx, e):
            return C.fail("You can set goals for yourself and your team.")
        g = app_tables.goals.add_row(company=cx.company, employee=e, title=title, due=d, progress=progress,
                                     status=status, created=C.now(), is_demo=False)
    return C.ok(goal=_goal(g))


@anvil.server.callable(require_user=True)
def delete_goal(goal_id):
    cx = W.ctx()
    g = W.row_in(cx, app_tables.goals, goal_id)
    if g is None:
        return C.ok()
    if not W.can_team(cx, g["employee"]):
        return C.fail("Only the person, their manager and HR can delete this goal.")
    g.delete()
    return C.ok()


# ------------------------------------------------------------------------------------------- kudos
def _kudos(k):
    g, r = k["giver"], k["receiver"]
    return {"id": k.get_id(), "from": W.name(g), "from_id": g.get_id() if g is not None else None,
            "to": W.name(r), "to_id": r.get_id() if r is not None else None, "to_initials": W.initials(r),
            "to_tone": W.tone(r), "from_initials": W.initials(g), "from_tone": W.tone(g),
            "value": k["value"] or "", "message": k["message"] or "", "created": C.iso(k["created"])}


def kudos_feed(company, limit=30):
    return [_kudos(k) for k in app_tables.kudos.search(tables.order_by("created", ascending=False), company=company)[:limit]]


def kudos_for(company, e):
    return [_kudos(k) for k in app_tables.kudos.search(tables.order_by("created", ascending=False), receiver=e)]


@anvil.server.callable(require_user=True)
def give_kudos(to_id, value, message):
    cx = W.ctx()
    r = W.emp_in(cx, to_id)
    message = C.text(message, 500, True)
    if r is None:
        return C.fail("Choose who the kudos are for.")
    if r == cx.emp:
        return C.fail("Kudos are for colleagues (we're sure you're great too).")
    if len(message) < 3:
        return C.fail("Say what they did.")
    if C.rate_limited("kudos", 20, 3600):
        return C.fail("That's a lot of kudos in one hour. Save some for tomorrow!")
    vals = W.settings(cx.company)["values"]
    k = app_tables.kudos.add_row(company=cx.company, giver=cx.emp, receiver=r, value=value if value in vals else "",
                                 message=message, created=C.now(), is_demo=False)
    return C.ok(kudos=_kudos(k))


# ------------------------------------------------------------------------------------------- reviews
def _cycle(c, cx):
    revs = app_tables.reviews.search(cycle=c)
    done = len([r for r in revs if r["status"] == "submitted"])
    return {"id": c.get_id(), "name": c["name"], "status": c["status"], "due": C.iso(c["due"]),
            "questions": list(c["questions"] or DEFAULT_QUESTIONS), "done": done, "total": len(revs),
            "created": C.iso(c["created"])}


def _review(r, cx):
    e, who, c = r["employee"], r["reviewer"], r["cycle"]
    return {"id": r.get_id(), "kind": r["kind"], "status": r["status"], "person": W.name(e),
            "person_id": e.get_id() if e is not None else None, "initials": W.initials(e), "tone": W.tone(e),
            "reviewer": W.name(who), "cycle": c["name"] if c is not None else "", "cycle_id": c.get_id() if c else None,
            "due": C.iso(c["due"]) if c is not None else None, "rating": r["rating"] or 0,
            "submitted_at": C.iso(r["submitted_at"]),
            "label": "Your self-review" if r["kind"] == "self" else "Review of %s" % W.name(e)}


def _can_read_review(cx, r):
    if cx.emp is not None and r["reviewer"] == cx.emp:
        return True
    if cx.is_admin:
        return True
    closed = r["cycle"] is not None and r["cycle"]["status"] == "closed"
    if cx.emp is not None and r["employee"] == cx.emp and r["status"] == "submitted" and closed:
        return True
    return r["status"] == "submitted" and W.is_above(cx.emp, r["employee"]) and r["kind"] == "self"


def reviews_to_write(cx):
    rows = app_tables.reviews.search(company=cx.company, reviewer=cx.emp, status="todo")
    return [_review(r, cx) for r in rows if r["cycle"] is not None and r["cycle"]["status"] == "open"]


@anvil.server.callable(require_user=True)
def start_cycle(name, due=None, questions=None):
    cx = W.ctx()
    W.require_admin(cx)
    import datetime as dt
    name = C.text(name, 80)
    if len(name) < 3:
        return C.fail("Name the cycle (e.g. Spring 2027 reviews).")
    try:
        d = dt.date.fromisoformat(str(due)[:10]) if due else C.now().date() + dt.timedelta(days=21)
    except ValueError:
        return C.fail("The due date isn't a date.")
    qs = [C.text(x, 300) for x in (questions or DEFAULT_QUESTIONS) if C.text(x, 300)][:8] or DEFAULT_QUESTIONS
    c = app_tables.review_cycles.add_row(company=cx.company, name=name, status="open", due=d, questions=qs,
                                         created=C.now(), is_demo=False)
    n = 0
    for e in W.active_people(cx.company):
        if e["status"] == "onboarding":
            continue
        app_tables.reviews.add_row(company=cx.company, cycle=c, employee=e, reviewer=e, kind="self", answers={},
                                   rating=0, status="todo", is_demo=False)
        n += 1
        if e["manager"] is not None:
            app_tables.reviews.add_row(company=cx.company, cycle=c, employee=e, reviewer=e["manager"], kind="manager",
                                       answers={}, rating=0, status="todo", is_demo=False)
            n += 1
    return C.ok(cycle=_cycle(c, cx), reviews=n)


@anvil.server.callable(require_user=True)
def get_review(review_id):
    cx = W.ctx()
    r = W.row_in(cx, app_tables.reviews, review_id)
    if r is None or not _can_read_review(cx, r):
        return C.fail("That review isn't one you can open.")
    c = r["cycle"]
    editable = cx.emp is not None and r["reviewer"] == cx.emp and c is not None and c["status"] == "open"
    goals = goals_for(r["employee"]) if W.can_team(cx, r["employee"]) else []
    return C.ok(review=_review(r, cx), questions=list(c["questions"] or DEFAULT_QUESTIONS) if c else DEFAULT_QUESTIONS,
                answers=dict(r["answers"] or {}), editable=editable, goals=goals)


@anvil.server.callable(require_user=True)
def save_review(review_id, answers, rating, submit=False):
    cx = W.ctx()
    r = W.row_in(cx, app_tables.reviews, review_id)
    if r is None or cx.emp is None or r["reviewer"] != cx.emp:
        return C.fail("Only the reviewer can write this review.")
    if r["cycle"] is None or r["cycle"]["status"] != "open":
        return C.fail("This review cycle is closed.")
    if not isinstance(answers, dict):
        return C.fail("Nothing to save.")
    clean = {str(k)[:4]: C.text(v, 4000, True) for k, v in list(answers.items())[:10]}
    try:
        rating = max(0, min(5, int(rating or 0)))
    except (TypeError, ValueError):
        rating = 0
    if submit:
        if rating < 1:
            return C.fail("Choose an overall rating before you submit.")
        if not any(clean.values()):
            return C.fail("Answer at least one question before you submit.")
    r.update(answers=clean, rating=rating, status="submitted" if submit else r["status"],
             submitted_at=C.now() if submit else r["submitted_at"])
    return C.ok(review=_review(r, cx))


@anvil.server.callable(require_user=True)
def cycle_status(cycle_id):
    cx = W.ctx()
    W.require_admin(cx)
    c = W.row_in(cx, app_tables.review_cycles, cycle_id)
    if c is None:
        return C.fail("That cycle no longer exists.")
    by_person: dict = {}
    for r in app_tables.reviews.search(cycle=c):
        e = r["employee"]
        if e is None:
            continue
        row = by_person.setdefault(e.get_id(), {"person": W.name(e), "person_id": e.get_id(), "initials": W.initials(e),
                                                "tone": W.tone(e), "department": e["department"] or "",
                                                "self": "none", "manager": "none", "rating": 0,
                                                "self_id": None, "manager_id": None, "reviewer": ""})
        row[r["kind"]] = r["status"]
        row[r["kind"] + "_id"] = r.get_id()
        if r["kind"] == "manager":
            row["rating"] = r["rating"] or 0
            row["reviewer"] = W.name(r["reviewer"])
    rows = sorted(by_person.values(), key=lambda x: x["person"].lower())
    dist = {str(n): len([x for x in rows if x["rating"] == n]) for n in range(1, 6)}
    return C.ok(cycle=_cycle(c, cx), rows=rows, distribution=dist)


@anvil.server.callable(require_user=True)
def close_cycle(cycle_id):
    cx = W.ctx()
    W.require_admin(cx)
    c = W.row_in(cx, app_tables.review_cycles, cycle_id)
    if c is None:
        return C.fail("That cycle no longer exists.")
    c["status"] = "closed"
    return C.ok(cycle=_cycle(c, cx))


# ------------------------------------------------------------------------------------------- pulse (eNPS)
def enps(scores):
    if not scores:
        return None
    pro = len([s for s in scores if s >= 9])
    det = len([s for s in scores if s <= 6])
    return round(100.0 * (pro - det) / len(scores))


def _survey(s, cx):
    answers = app_tables.survey_answers.search(survey=s)
    n = len(answers)
    answered = cx.emp is not None and app_tables.survey_done.get(survey=s, employee=cx.emp) is not None
    d = {"id": s.get_id(), "question": s["question"], "status": s["status"], "created": C.iso(s["created"]),
         "answers": n, "answered": answered, "visible": n >= MIN_ANSWERS, "min": MIN_ANSWERS,
         "invited": len(W.active_people(cx.company))}
    if n >= MIN_ANSWERS:
        scores = [a["score"] or 0 for a in answers]
        d["enps"] = enps(scores)
        d["promoters"] = len([x for x in scores if x >= 9])
        d["passives"] = len([x for x in scores if 7 <= x <= 8])
        d["detractors"] = len([x for x in scores if x <= 6])
        d["comments"] = [a["comment"] for a in sorted(answers, key=lambda a: a["created"] or C.now(), reverse=True)
                         if a["comment"]][:40]
    return d


def open_survey_for(cx):
    for s in app_tables.surveys.search(tables.order_by("created", ascending=False), company=cx.company, status="open"):
        if cx.emp is not None and app_tables.survey_done.get(survey=s, employee=cx.emp) is None:
            return _survey(s, cx)
    return None


@anvil.server.callable(require_user=True)
def start_survey(question=""):
    cx = W.ctx()
    W.require_admin(cx)
    q = C.text(question, 200) or "How likely are you to recommend %s as a place to work? (0-10)" % cx.company["name"]
    for s in app_tables.surveys.search(company=cx.company, status="open"):
        s["status"] = "closed"
    s = app_tables.surveys.add_row(company=cx.company, question=q, status="open", created=C.now(), is_demo=False)
    return C.ok(survey=_survey(s, cx))


@anvil.server.callable(require_user=True)
def answer_survey(survey_id, score, comment=""):
    cx = W.ctx()
    s = W.row_in(cx, app_tables.surveys, survey_id)
    if s is None or s["status"] != "open":
        return C.fail("This survey is closed.")
    if cx.viewing_as:
        return C.fail("Answers are anonymous, so they can't be given while previewing as someone else.")
    if app_tables.survey_done.get(survey=s, employee=cx.emp) is not None:
        return C.fail("You've already answered. Thank you!")
    try:
        score = int(score)
    except (TypeError, ValueError):
        return C.fail("Choose a score from 0 to 10.")
    if not 0 <= score <= 10:
        return C.fail("Choose a score from 0 to 10.")
    app_tables.survey_done.add_row(company=cx.company, survey=s, employee=cx.emp, is_demo=False)
    app_tables.survey_answers.add_row(company=cx.company, survey=s, score=score, comment=C.text(comment, 1000, True),
                                      created=C.now().replace(minute=0, second=0, microsecond=0), is_demo=False)
    return C.ok()


@anvil.server.callable(require_user=True)
def close_survey(survey_id):
    cx = W.ctx()
    W.require_admin(cx)
    s = W.row_in(cx, app_tables.surveys, survey_id)
    if s is not None:
        s["status"] = "closed"
    return C.ok()


@anvil.server.callable(require_user=True)
def performance_overview():
    cx = W.ctx()
    cycles = app_tables.review_cycles.search(tables.order_by("created", ascending=False), company=cx.company)
    team = W.reports_of(cx.company, cx.emp) if cx.emp is not None else []
    team_goals = []
    for e in team[:40]:
        team_goals += goals_for(e)
    surveys = app_tables.surveys.search(tables.order_by("created", ascending=False), company=cx.company)
    peers = sorted([p for p in W.active_people(cx.company) if p != cx.emp], key=lambda p: W.name(p).lower())
    mine_written = [_review(r, cx) for r in app_tables.reviews.search(company=cx.company, employee=cx.emp,
                                                                       status="submitted") if _can_read_review(cx, r)]
    return {"to_write": reviews_to_write(cx), "about_me": mine_written,
            "cycles": [_cycle(c, cx) for c in cycles] if cx.is_admin else
            [_cycle(c, cx) for c in cycles if c["status"] == "open"],
            "my_goals": goals_for(cx.emp), "team_goals": team_goals, "kudos": kudos_feed(cx.company),
            "values": list(W.settings(cx.company)["values"]), "survey": open_survey_for(cx),
            "surveys": [_survey(s, cx) for s in surveys[:8]] if cx.is_admin else [],
            "people": [{"id": p.get_id(), "name": W.name(p)} for p in peers],
            "is_admin": cx.is_admin, "is_manager": len(team) > 0, "me_id": cx.emp.get_id() if cx.emp else None,
            "default_questions": DEFAULT_QUESTIONS}
