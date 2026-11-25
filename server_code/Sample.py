"""Sample company data, so a new workspace (and the public demo careers page) is alive from the first minute.

Every name and company here is fictional. Dates are relative to today, so the sample never goes stale.
Sample rows have is_demo=True; remove(company) deletes them (and anything real that hangs off them), leaving the
company's real people, settings, leave types and holidays alone. Leaf rows go in with add_rows (a few calls),
so seeding stays well under Anvil's 30-second call limit."""
import datetime as dt
import random

from anvil.tables import app_tables

from . import common as C
from . import Workspace as W

LEAVE_TYPES = [("Vacation", 20, True, "spruce"), ("Sick", 10, True, "amber"), ("Personal", 3, True, "sky"),
               ("Parental", 0, True, "plum"), ("Unpaid", 0, False, "slate")]
HOLIDAYS = [("New Year's Day", "2026-01-01"), ("Good Friday", "2026-04-03"), ("Victoria Day", "2026-05-18"),
            ("Saint-Jean-Baptiste", "2026-06-24"), ("Canada Day", "2026-07-01"), ("Labour Day", "2026-09-07"),
            ("Thanksgiving", "2026-10-12"), ("Christmas Day", "2026-12-25"), ("Boxing Day", "2026-12-26"),
            ("New Year's Day", "2027-01-01"), ("Good Friday", "2027-03-26"), ("Victoria Day", "2027-05-24"),
            ("Saint-Jean-Baptiste", "2027-06-24"), ("Canada Day", "2027-07-01"), ("Labour Day", "2027-09-06"),
            ("Thanksgiving", "2027-10-11"), ("Christmas Day", "2027-12-25"), ("Boxing Day", "2027-12-26")]

# key, first, last, preferred, pronouns, title, department, location, manager key, years ago started, pay, type
PEOPLE = [
    ("ceo", "Amara", "Okafor", "", "she/her", "Chief Executive Officer", "Leadership", "Montréal", None, 6.2, 210000, "Full-time"),
    ("cto", "Mateus", "Silva", "", "he/him", "Chief Technology Officer", "Engineering", "Montréal", "ceo", 5.8, 195000, "Full-time"),
    ("hrg", "Priya", "Raman", "", "she/her", "People Partner", "People", "Montréal", "me", 2.4, 86000, "Full-time"),
    ("eng", "Lena", "Fischer", "", "she/her", "Engineering Manager", "Engineering", "Montréal", "cto", 4.1, 152000, "Full-time"),
    ("be1", "Kwame", "Mensah", "", "he/him", "Senior Backend Engineer", "Engineering", "Remote", "eng", 3.3, 138000, "Full-time"),
    ("be2", "Yuki", "Tanaka", "", "they/them", "Backend Engineer", "Engineering", "Montréal", "eng", 1.6, 112000, "Full-time"),
    ("fe1", "Bartholomew", "Wolfeschlegelsteinhausen-Bergerdorff", "Bart", "he/him", "Frontend Engineer", "Engineering", "Remote", "eng", 2.0, 118000, "Full-time"),
    ("fe2", "Sofia", "Marchetti", "", "she/her", "Frontend Engineer", "Engineering", "Montréal", "eng", 0.03, 108000, "Full-time"),
    ("qa1", "Diego", "Ramírez", "", "he/him", "QA Engineer", "Engineering", "Montréal", "eng", 2.8, 96000, "Full-time"),
    ("int", "J", "Okonkwo-Lee", "", "he/him", "Engineering Intern", "Engineering", "Montréal", "eng", 0.25, 24.0, "Intern"),
    ("des", "Noor", "Haddad", "", "she/her", "Design Lead", "Design", "Montréal", "cto", 3.9, 128000, "Full-time"),
    ("ds1", "Émile", "Gagnon", "", "he/him", "Product Designer", "Design", "Montréal", "des", 1.2, 98000, "Full-time"),
    ("ds2", "Hana", "Novak", "", "she/her", "Brand Designer", "Design", "Remote", "des", 0.8, 52.0, "Contractor"),
    ("sal", "Grace", "Kim", "", "she/her", "Head of Sales", "Sales", "Montréal", "ceo", 4.6, 140000, "Full-time"),
    ("ae1", "Oliver", "Bennett", "", "he/him", "Account Executive", "Sales", "Montréal", "sal", 1.9, 82000, "Full-time"),
    ("ae2", "Fatima", "Zahra", "", "she/her", "Account Executive", "Sales", "Remote", "sal", 1.1, 80000, "Full-time"),
    ("sdr", "Lucas", "Tremblay", "", "he/him", "Sales Development Rep", "Sales", "Montréal", "sal", 0.6, 62000, "Full-time"),
    ("csm", "Mei", "Chen", "", "she/her", "Customer Success Manager", "Sales", "Montréal", "sal", 2.7, 88000, "Full-time"),
    ("ops", "Tomasz", "Nowak", "", "he/him", "Head of Operations", "Operations", "Montréal", "ceo", 5.1, 132000, "Full-time"),
    ("fin", "Aisha", "Bello", "", "she/her", "Finance Manager", "Operations", "Montréal", "ops", 3.0, 104000, "Full-time"),
    ("off", "Rafael", "Costa", "", "he/him", "Office Coordinator", "Operations", "Montréal", "ops", 1.4, 30.0, "Part-time"),
    ("it1", "Ingrid", "Larsen", "", "she/her", "IT Administrator", "Operations", "Montréal", "ops", 2.2, 84000, "Full-time"),
    ("par", "Chloé", "Dubois", "", "she/her", "Customer Success Lead", "Sales", "Montréal", "sal", 3.6, 99000, "Full-time"),
    ("new", "Jonah", "Reyes", "", "he/him", "Backend Engineer", "Engineering", "Remote", "eng", -9 / 365.25, 114000, "Full-time"),
    ("lvr", "Marc", "Lefebvre", "", "he/him", "Senior Account Executive", "Sales", "Montréal", "sal", 4.0, 98000, "Full-time"),
    ("old", "Nadia", "Petrova", "", "she/her", "Data Analyst", "Operations", "Remote", "ops", 2.5, 90000, "Full-time"),
]
ABOUT = {
    "ceo": "Started the company in a borrowed meeting room. Ask me about sourdough or board games.",
    "hrg": "Here for anything people-related: leave, benefits, awkward questions. My door is open.",
    "fe1": "Accessibility nerd. My surname is long, so Bart is fine. Supercalifragilisticexpialidociouslylongword.",
    "des": "Design systems, type and very strong coffee.",
    "it1": "Laptop trouble? Badge not working? Message me before you restart anything twice.",
}
JOBS = [
    ("Senior Backend Engineer", "Engineering", "Remote", "eng", "open", "$130k-$150k",
     "Build the services behind our product. You'll own APIs end to end, mentor two engineers and help us scale from "
     "hundreds to thousands of customers.\n\nWhat you'll do\n- Design and ship backend features\n- Improve reliability "
     "and observability\n- Review code and pair with the team\n\nWhat we look for\n- 5+ years building web backends\n"
     "- Comfortable with Python and SQL\n- Clear writing"),
    ("Account Executive", "Sales", "Montréal", "sal", "open", "$75k-$90k + commission",
     "Run the full sales cycle with small and mid-size companies across Canada. Bilingual (French and English) is a plus."),
    ("People Operations Coordinator", "People", "Montréal", "me", "open", "$58k-$66k",
     "Keep people operations running smoothly: onboarding, records, time off questions and our yearly review cycle."),
    ("Product Designer", "Design", "Montréal", "des", "draft", "$95k-$110k", "Draft: waiting for budget approval."),
]
CANDIDATES = [
    (0, "Ana Lucía Ortega", "interview", 4, "Referral"), (0, "Ben Adeyemi", "offer", 5, "LinkedIn"),
    (0, "Claire Fontaine", "screen", 3, "Careers page"), (0, "Dev Malhotra", "applied", 0, "Careers page"),
    (0, "Elif Yılmaz", "applied", 0, "Job board"), (0, "Frank Osei", "rejected", 2, "Agency"),
    (0, "Gabriela Souza", "interview", 4, "Careers page"), (0, "Hiroshi Ito", "applied", 0, "LinkedIn"),
    (1, "Isabelle Roy", "screen", 4, "Referral"), (1, "Jamal Carter", "applied", 0, "Careers page"),
    (1, "Karin Holm", "interview", 3, "Job board"), (1, "Léa Morin", "applied", 0, "Careers page"),
    (2, "Maya Goldberg", "interview", 5, "Careers page"), (2, "Nikhil Rao", "applied", 0, "LinkedIn"),
    (2, "Olga Ivanova", "screen", 3, "Referral"),
]
POLICIES = [
    ("Employee handbook", True,
     "Welcome! This handbook explains how we work together.\n\nWorking hours\nCore hours are 10:00 to 15:00 Eastern. "
     "Outside them, plan your day the way that works for you and your team.\n\nTime off\nYou get 20 vacation days a "
     "year plus public holidays. Ask in the app at least two weeks ahead for anything longer than three days.\n\n"
     "Sick days\nTake them when you need them. Tell your manager the same morning; no doctor's note is needed for "
     "the first three days.\n\nEquipment\nYou'll get a laptop on day one. Look after it and return it when you leave."),
    ("Remote and hybrid work", True,
     "Most roles can work remotely from Canada. Come to the Montréal office for team days (usually every other "
     "Tuesday). We pay up to $500 once for a home office setup and $40 a month for internet."),
    ("Code of conduct", True,
     "Treat everyone with respect. Harassment and discrimination are never acceptable. If something happens, talk to "
     "your manager or People; you can also report anonymously. Nobody will be punished for raising a concern in good faith."),
    ("Expenses and travel", False,
     "Book travel through Finance. Keep receipts for anything over $25. Meals while travelling: up to $75 a day. "
     "Submit expenses within 30 days."),
]
GOALS = [("be1", "Cut API response time (p95) under 200 ms", 70, "on_track"),
         ("be1", "Mentor Jonah through his first quarter", 20, "on_track"),
         ("eng", "Ship the new reporting service", 55, "at_risk"), ("ae1", "Close $400k in new business", 62, "on_track"),
         ("ds1", "Run 10 customer interviews for onboarding", 100, "done"), ("hrg", "Refresh the employee handbook", 80, "on_track"),
         ("me", "Launch the autumn review cycle", 90, "on_track"), ("me", "Get eNPS above 30", 40, "at_risk"),
         ("csm", "Keep logo churn under 3%", 75, "on_track"), ("fe1", "WCAG 2.2 AA on every screen", 35, "off_track")]
KUDOS = [("eng", "be1", "Own it", "Stayed calm through the Friday outage and wrote the clearest incident report I've read."),
         ("sal", "ae2", "Ship it", "Closed the Laval deal two weeks early. Fantastic work!"),
         ("hrg", "fe2", "Be kind", "Welcomed Sofia with a hand-drawn map of the office. Small thing, huge impact."),
         ("des", "fe1", "Stay curious", "Taught the whole team how screen readers announce our dialogs."),
         ("ops", "it1", "Own it", "Had every new laptop ready the day before people started. Every single time."),
         ("cto", "qa1", "Ship it", "Found the billing bug before a single customer did.")]
ANNOUNCEMENTS = [
    ("Office closed for the holidays", "The office is closed from 24 December to 2 January. Enjoy the break!", True, "ceo"),
    ("Welcome Sofia and Jonah!", "Sofia joined Engineering last week and Jonah starts soon. Say hi in #general.", False, "me"),
    ("Autumn reviews are open", "Self-reviews and manager reviews are due in ten days. They take about 30 minutes.", False, "me"),
]
COMMENTS = ["Great team, I learn something every week.", "More clarity on priorities would help.",
            "Love the flexibility.", "Meetings could be shorter.", "Proud of what we ship.",
            "Career paths feel unclear in Sales.", "Best manager I've had."]


def defaults(company):
    """Leave types and holidays every new company starts with (real rows, kept when sample data is removed)."""
    if len(app_tables.leave_types.search(company=company)) == 0:
        app_tables.leave_types.add_rows([dict(company=company, name=n, allowance=a, paid=p, color=c, order=i, is_demo=False)
                                         for i, (n, a, p, c) in enumerate(LEAVE_TYPES)])
    if len(app_tables.holidays.search(company=company)) == 0:
        app_tables.holidays.add_rows([dict(company=company, name=n, date=dt.date.fromisoformat(d), is_demo=False)
                                      for n, d in HOLIDAYS])


def _workday(d, step=1):
    while d.weekday() >= 5:
        d += dt.timedelta(days=step)
    return d


def seed(company, me=None):
    rnd = random.Random(company["name"])
    today = C.now().date()
    now = C.now()
    defaults(company)
    types = {t["name"]: t for t in app_tables.leave_types.search(company=company)}
    emp = {"me": me} if me is not None else {}
    changes = []
    for key, first, last, pref, pro, title, dept, loc, mgr, yrs, pay, typ in PEOPLE:
        start = today - dt.timedelta(days=int(yrs * 365.25))
        b = dt.date(1975 + rnd.randint(0, 25), rnd.randint(1, 12), rnd.randint(1, 28))
        if key in ("hrg", "be2"):
            b = (today + dt.timedelta(days=4 if key == "hrg" else 17)).replace(year=1992)
        hourly = pay < 1000
        e = app_tables.employees.add_row(
            company=company, first_name=first, last_name=last, preferred_name=pref, pronouns=pro,
            work_email="%s.%s@sample.example" % (first.lower()[:12], last.lower().split("-")[0][:14]),
            title=title, department=dept, location=loc, employment_type=typ, start_date=start,
            status="onboarding" if start > today else "active", role="manager" if key in ("cto", "eng", "des", "sal", "ops", "ceo") else "employee",
            pay_rate=pay, pay_period="hour" if hourly else "year", pay_currency=company["currency"] or "CAD",
            pay_effective=start + dt.timedelta(days=365 * int(max(0, yrs - 0.5))) if yrs > 1 else start,
            birthday=b, phone="+1 514 555 %04d" % rnd.randint(100, 9999), about=ABOUT.get(key, ""),
            emergency={"name": "Sample contact", "relation": "Partner", "phone": "+1 514 555 0100"},
            created=now, is_demo=True)
        emp[key] = e
        changes.append(dict(company=company, employee=e, kind="status", field="Status", old="", new="Hired as " + title,
                            effective=start, by_name="People team", when=now - dt.timedelta(days=max(0, int(yrs * 365))),
                            is_demo=True))
        if yrs > 1.5 and not hourly:
            changes.append(dict(company=company, employee=e, kind="pay", field="Pay rate", old="%g" % round(pay * 0.94),
                                new="%g" % pay, effective=today - dt.timedelta(days=int((yrs % 1) * 300) + 30),
                                by_name="People team", when=now - dt.timedelta(days=40), is_demo=True))
    for row in PEOPLE:
        key, mgr = row[0], row[8]
        if mgr and mgr in emp:
            emp[key]["manager"] = emp[mgr]
        elif mgr == "me":
            emp[key]["manager"] = emp["ceo"]
    if me is not None:
        me.update(manager=emp["ceo"], birthday=me["birthday"] or dt.date(1988, (today.month % 12) + 1, 9))
    emp["par"]["status"] = "leave"
    changes.append(dict(company=company, employee=emp["par"], kind="status", field="Status", old="active", new="leave",
                        effective=today - dt.timedelta(days=40), by_name="People team", when=now, is_demo=True))
    changes.append(dict(company=company, employee=emp["ds1"], kind="job", field="Job title", old="Junior Product Designer",
                        new="Product Designer", effective=today - dt.timedelta(days=60), by_name="People team",
                        when=now - dt.timedelta(days=60), is_demo=True))
    old = emp["old"]
    old.update(status="terminated", end_date=today - dt.timedelta(days=35),
               termination={"reason": "Resignation", "regretted": True, "rehire": True, "note": "Moved to a startup."})
    lvr = emp["lvr"]
    lvr.update(end_date=_workday(today + dt.timedelta(days=14)),
               termination={"reason": "Resignation", "regretted": False, "rehire": True, "note": "Moving abroad."})
    for e, txt, d in ((old, "Leaving: Resignation", old["end_date"]), (lvr, "Leaving: Resignation", lvr["end_date"])):
        changes.append(dict(company=company, employee=e, kind="status", field="Status", old="", new=txt, effective=d,
                            by_name="People team", when=now - dt.timedelta(days=20), is_demo=True))
    app_tables.changes.add_rows(changes)

    # time off: a past year of approved leave, who's out this week, pending requests to approve
    reqs = []

    def req(key, typ, start, days, status, note=""):
        s = _workday(start)
        end, n = s, 1
        while n < days:
            end = _workday(end + dt.timedelta(days=1))
            n += 1
        reqs.append(dict(company=company, employee=emp[key], leave_type=types[typ], start=s, end=end, days=days,
                         note=note, status=status, decided_by_name="Amara Okafor" if status != "pending" else None,
                         decided_at=now - dt.timedelta(days=3) if status != "pending" else None,
                         created=now - dt.timedelta(days=10), is_demo=True))
    for key, *_ in PEOPLE:
        if key in ("new", "old", "int", "fe2"):
            continue
        base = today.replace(month=1, day=8) + dt.timedelta(days=rnd.randint(0, 200))
        if base < today - dt.timedelta(days=5):
            req(key, "Vacation", base, rnd.choice([2, 3, 5]), "approved", "Family trip")
        if rnd.random() < 0.5:
            sick = today - dt.timedelta(days=rnd.randint(10, 150))
            req(key, "Sick", sick, 1, "approved")
    req("be1", "Vacation", today, 3, "approved", "Long weekend in Québec City")
    req("ae1", "Personal", today + dt.timedelta(days=2), 1, "approved", "Moving day")
    req("ds1", "Vacation", today + dt.timedelta(days=1), 2, "approved")
    req("par", "Parental", today - dt.timedelta(days=40), 90, "approved", "Parental leave")
    req("hrg", "Vacation", today + dt.timedelta(days=21), 5, "pending", "Lisbon with my sister")
    req("qa1", "Vacation", today + dt.timedelta(days=12), 3, "pending")
    req("csm", "Personal", today + dt.timedelta(days=6), 1, "pending", "Citizenship ceremony")
    req("ae2", "Vacation", today + dt.timedelta(days=30), 4, "declined", "")
    app_tables.leave_requests.add_rows(reqs)

    # hiring
    jobs = []
    for title, dept, loc, mgr, status, sal, desc in JOBS:
        jobs.append(app_tables.jobs.add_row(company=company, title=title, department=dept, location=loc,
                                            employment_type="Full-time", description=desc, status=status,
                                            hiring_manager=emp.get(mgr) or emp["ceo"], salary_range=sal,
                                            created=now - dt.timedelta(days=rnd.randint(6, 40)), is_demo=True))
    cands = []
    for i, (j, name, stage, rating, source) in enumerate(CANDIDATES):
        notes = [{"by": "Priya Raman", "text": "Strong portfolio, clear communicator.", "when": C.iso(now - dt.timedelta(days=4))}] \
            if rating >= 4 else []
        cands.append(dict(company=company, job=jobs[j], name=name, email="%s@candidate.example" % name.split()[0].lower(),
                          phone="", link="", cover="I'd love to join because your product makes HR feel human.",
                          stage=stage, rating=rating, source=source, notes=notes,
                          created=now - dt.timedelta(days=rnd.randint(0, 20), hours=i), is_demo=True))
    app_tables.candidates.add_rows(cands)

    # onboarding + offboarding checklists
    tasks = []
    s = W.settings(company)
    for e, kind, done_upto in ((emp["new"], "onboarding", 2), (emp["fe2"], "onboarding", 5), (lvr, "offboarding", 1)):
        base = e["start_date"] if kind == "onboarding" else e["end_date"]
        cl = app_tables.checklists.add_row(company=company, employee=e, kind=kind,
                                           title=("Welcome %s" if kind == "onboarding" else "Goodbye %s") % W.name(e),
                                           created=now - dt.timedelta(days=12), is_demo=True)
        for i, t in enumerate(s[kind]):
            done = i < done_upto
            tasks.append(dict(company=company, checklist=cl, employee=e, title=t["title"], owner_role=t["role"],
                              due=base + dt.timedelta(days=int(t["day"])), order=i,
                              done_at=now - dt.timedelta(days=2) if done else None,
                              done_by_name="Priya Raman" if done else None, is_demo=True))
    app_tables.tasks.add_rows(tasks)

    # performance: an open review cycle, goals, kudos
    cycle = app_tables.review_cycles.add_row(company=company, name="Autumn %d reviews" % today.year, status="open",
                                             due=today + dt.timedelta(days=10), questions=None,
                                             created=now - dt.timedelta(days=11), is_demo=True)
    from . import Perform
    cycle["questions"] = list(Perform.DEFAULT_QUESTIONS)
    revs = []
    for key, e in emp.items():
        if e["status"] in ("onboarding", "terminated"):
            continue
        sub = key not in ("me", "hrg", "be2", "fe1", "ae2") and rnd.random() < 0.6
        revs.append(dict(company=company, cycle=cycle, employee=e, reviewer=e, kind="self",
                         answers={"0": "Shipped what I promised and helped others."} if sub else {},
                         rating=rnd.choice([3, 4, 4, 5]) if sub else 0, status="submitted" if sub else "todo",
                         submitted_at=now - dt.timedelta(days=2) if sub else None, is_demo=True))
        m = e["manager"]
        if m is not None:
            msub = sub and rnd.random() < 0.6 and m != me
            revs.append(dict(company=company, cycle=cycle, employee=e, reviewer=m, kind="manager",
                             answers={"0": "Reliable, kind, and raised the bar."} if msub else {},
                             rating=rnd.choice([3, 3, 4, 4, 5]) if msub else 0, status="submitted" if msub else "todo",
                             submitted_at=now - dt.timedelta(days=1) if msub else None, is_demo=True))
    app_tables.reviews.add_rows(revs)
    app_tables.goals.add_rows([dict(company=company, employee=emp[k], title=t, progress=p, status=st,
                                    due=today + dt.timedelta(days=rnd.randint(20, 90)), created=now, is_demo=True)
                               for k, t, p, st in GOALS if k in emp])
    app_tables.kudos.add_rows([dict(company=company, giver=emp[g], receiver=emp[r], value=v, message=m,
                                    created=now - dt.timedelta(days=i * 2 + 1, hours=i), is_demo=True)
                               for i, (g, r, v, m) in enumerate(KUDOS)])

    # pulse: last quarter's results + one open survey
    q = "How likely are you to recommend %s as a place to work? (0-10)" % company["name"]
    past = app_tables.surveys.add_row(company=company, question=q, status="closed", created=now - dt.timedelta(days=95),
                                      is_demo=True)
    live = app_tables.surveys.add_row(company=company, question=q, status="open", created=now - dt.timedelta(days=4),
                                      is_demo=True)
    answers, done = [], []
    people = [e for k, e in emp.items() if k != "me" and e["status"] != "onboarding"]
    for survey, n, lo in ((past, 18, 6), (live, 9, 7)):
        pool = people if survey == past else [e for e in people if e != emp["hrg"]]
        for i, e in enumerate(pool[:n]):
            answers.append(dict(company=company, survey=survey, score=rnd.randint(lo, 10),
                                comment=COMMENTS[i % len(COMMENTS)] if i % 3 == 0 else "",
                                created=survey["created"] + dt.timedelta(hours=i), is_demo=True))
            done.append(dict(company=company, survey=survey, employee=e, is_demo=True))
    app_tables.survey_answers.add_rows(answers)
    app_tables.survey_done.add_rows(done)

    # policies (+ who acknowledged), announcements, equipment
    acks = []
    for title, need, body in POLICIES:
        p = app_tables.policies.add_row(company=company, title=title, body=body, require_ack=need,
                                        updated=now - dt.timedelta(days=60), is_demo=True)
        if need:
            for e in people:
                if rnd.random() < 0.8:
                    acks.append(dict(company=company, policy=p, employee=e, when=now - dt.timedelta(days=rnd.randint(1, 50)),
                                     is_demo=True))
    app_tables.acks.add_rows(acks)
    app_tables.announcements.add_rows([dict(company=company, title=t, body=b, pinned=pin, author=emp.get(a) or emp["ceo"],
                                            created=now - dt.timedelta(days=i * 3, hours=2), is_demo=True)
                                       for i, (t, b, pin, a) in enumerate(ANNOUNCEMENTS)])
    assets = []
    for i, (key, e) in enumerate(emp.items()):
        if key in ("new",) or e["status"] == "terminated":
            continue
        mac = key in ("des", "ds1", "ds2", "fe1", "fe2")
        assets.append(dict(company=company, employee=e, kind="Laptop", name="MacBook Pro 14" if mac else "ThinkPad X1 Carbon",
                           serial="SN-%05d" % (1000 + i * 37), assigned=e["start_date"] or today, is_demo=True))
        if i % 3 == 0:
            assets.append(dict(company=company, employee=e, kind="Badge", name="Office badge", serial="B-%03d" % i,
                               assigned=e["start_date"] or today, is_demo=True))
    app_tables.assets.add_rows(assets)
    return len(emp)


SAMPLE_TABLES = ["survey_done", "survey_answers", "surveys", "acks", "policies", "announcements", "kudos", "reviews",
                 "review_cycles", "goals", "tasks", "checklists", "candidates", "jobs", "leave_requests", "assets",
                 "files", "changes"]


def remove(company):
    """Delete sample rows (and real rows that point at them) of one company. Returns how many rows went."""
    demo_emps = list(app_tables.employees.search(company=company, is_demo=True))
    demo_set = set(e.get_id() for e in demo_emps)
    gone = set()

    def is_demo_link(v):
        return v is not None and (v.get_id() in demo_set or v.get_id() in gone)

    n = 0
    for e in app_tables.employees.search(company=company, is_demo=False):
        if is_demo_link(e["manager"]):
            e["manager"] = None
    for j in app_tables.jobs.search(company=company, is_demo=False):
        if is_demo_link(j["hiring_manager"]):
            j["hiring_manager"] = None
    order = list(reversed(SAMPLE_TABLES))  # parents first, so children can see them in `gone`
    parents = {"surveys": [], "policies": [], "review_cycles": [], "checklists": [], "jobs": []}
    for t in order:
        for r in getattr(app_tables, t).search(company=company, is_demo=True):
            if t in parents:
                gone.add(r.get_id())
    links = ["employee", "giver", "receiver", "reviewer", "author", "policy", "survey", "cycle", "checklist", "job"]
    for t in SAMPLE_TABLES:
        table = getattr(app_tables, t)
        cols = set(c["name"] for c in table.list_columns())
        for r in table.search(company=company):
            if r["is_demo"] or any(is_demo_link(r[c]) for c in links if c in cols):
                r.delete()
                n += 1
    for e in demo_emps:
        e.delete()
        n += 1
    return n
