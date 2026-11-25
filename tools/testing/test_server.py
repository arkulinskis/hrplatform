"""Server tests against the strict mock of Anvil (tools/testing/mock).

    python tools/testing/test_server.py          -> prints ALL OK, or the first failure

call(name, ...) runs a server function the way the browser does: by name, with require_user enforced,
and the reply must be JSON (a datetime or a row in a reply fails here, like it would break the page).
Add tests for every new server function: the happy path, bad input, and someone who isn't allowed.
"""
import datetime as dt
import importlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
_tmp = pathlib.Path(tempfile.mkdtemp())
shutil.copytree(PROJECT / "server_code", _tmp / "app")
(_tmp / "app" / "__init__.py").write_text("")
os.environ["ANVIL_APP_YAML"] = str(PROJECT / "anvil.yaml")  # the mock's tables follow the app's own schema
sys.path[:0] = [str(HERE / "mock"), str(_tmp)]
import anvil.server  # noqa: E402
import anvil.users  # noqa: E402
import anvil.secrets  # noqa: E402
anvil.secrets.SECRETS["admin_emails"] = "admin@example.com"  # the App Secret, faked
from anvil.tables import app_tables as T  # noqa: E402

M = {p.stem: importlib.import_module("app." + p.stem) for p in sorted((PROJECT / "server_code").glob("*.py"))}
now = dt.datetime.now(dt.timezone.utc)


def call(name, *args):
    r = anvil.server.call(name, *args)
    json.dumps(r)  # strict: must be JSON-able
    return r


def as_user(row):
    anvil.users.CURRENT[0] = row
    anvil.server.session.use(row.get_id() if row is not None else None)


def denied(name, *args):
    try:
        call(name, *args)
    except anvil.server.PermissionDenied:
        return True
    return False


def ok(r, msg=""):
    assert isinstance(r, dict) and r.get("ok"), (msg, r)
    return r


def bad(r, msg=""):
    assert isinstance(r, dict) and r.get("ok") is False and r.get("error"), (msg, r)
    return r


def person(email, name=None, **kw):
    return T.users.add_row(email=email, enabled=True, signed_up=now, display_name=name, **kw)


# ---------------------------------------------------------------------------------- accounts
admin = person("admin@example.com", "The Admin")
ana = person("ana@example.com", "Ana")
bob = person("bob@example.com")

as_user(None)
assert call("get_me") is None
assert denied("update_profile", "X")
as_user(admin)
assert call("get_me")["is_admin"] is True, "ADMIN_EMAILS become admins on first sign-in"
as_user(ana)
me = call("get_me")
assert me["name"] == "Ana" and me["is_admin"] is False
assert ana["last_seen"] is not None
as_user(bob)
assert call("get_me")["name"] == "Bob", "a name comes from the email when none is set"
bad(call("update_profile", " x "))
assert ok(call("update_profile", "  Bob   Stone "))["me"]["name"] == "Bob Stone"

# ---------------------------------------------------------------------------------- feedback
as_user(None)
bad(call("submit_feedback", "bug", "hi"))
ok(call("submit_feedback", "bug", "The button is broken", "guest@example.com", {"page": "#home", "evil": "x" * 9999}))
fb = T.feedback.search()[0]
assert fb["name"] == "Guest" and fb["email"] == "guest@example.com" and "evil" not in fb["context"] and fb["status"] == "new"
for i in range(4):
    ok(call("submit_feedback", "idea", "Idea number %d" % i))
bad(call("submit_feedback", "idea", "One too many this hour"), "rate limit")
as_user(ana)
ok(call("submit_feedback", "nonsense-kind", "Signed-in feedback"))
assert T.feedback.get(message="Signed-in feedback")["kind"] == "other"
assert denied("list_feedback")
as_user(admin)
lst = call("list_feedback")
assert lst["counts"]["new"] == 6 and len(lst["items"]) == 6
fid = lst["items"][0]["id"]
ok(call("set_feedback_status", fid, "done", "Fixed it"))
assert call("list_feedback", "done")["items"][0]["note"] == "Fixed it"
bad(call("set_feedback_status", fid, "weird"))
bad(call("set_feedback_status", "nope", "done"))
ok(call("delete_feedback", fid))
assert len(call("list_feedback")["items"]) == 5

# ---------------------------------------------------------------------------------- admin
as_user(ana)
for fn, args in [("admin_overview", ()), ("list_users", ()), ("set_admin", (bob.get_id(), True)), ("demo_load", ()), ("demo_remove", ())]:
    assert denied(fn, *args), fn
as_user(admin)
ov = call("admin_overview")
assert ov["users"] == 3 and ov["admins"] == 1 and ov["feedback_new"] == 5
assert len(call("list_users")["users"]) == 3 and len(call("list_users", "bob")["users"]) == 1
ok(call("set_admin", bob.get_id(), True))
assert bob["is_admin"] is True
bad(call("set_admin", admin.get_id(), False), "can't remove your own admin")
ok(call("set_enabled", bob.get_id(), False))
assert bob["enabled"] is False
bad(call("set_enabled", admin.get_id(), False))
ok(call("set_enabled", bob.get_id(), True))
ok(call("set_admin", bob.get_id(), False))
assert bob["is_admin"] is False

# ---------------------------------------------------------------------------------- demo company (public careers page)
as_user(None)
cp = ok(call("careers_page", "larkspur"))
assert M["DemoData"].state() == "loaded" and cp["demo"] and len(cp["jobs"]) == 3, "demo company loads on first visit"
bad(call("careers_page", "no-such-company"))
job0 = cp["jobs"][0]["id"]
ok(call("apply_to_job", job0, {"name": "Bot", "email": "b@x.y", "website": "spam", "ms": 9000}))
ok(call("apply_to_job", job0, {"name": "Too Fast", "email": "f@x.y", "ms": 100}))
assert not T.candidates.search(name="Bot") and not T.candidates.search(name="Too Fast"), "spam guards drop silently"
bad(call("apply_to_job", job0, {"name": "X", "email": "nope", "ms": 9000}))
ok(call("apply_to_job", job0, {"name": "Real Person", "email": "real@x.y", "ms": 9000, "cover": "Hi"}))
ok(call("apply_to_job", job0, {"name": "Real Person", "email": "real@x.y", "ms": 9000}))
assert len(T.candidates.search(name="Real Person")) == 1, "no duplicate applications"
as_user(admin)
ok(call("demo_load"))
ok(call("demo_load"))
assert len(T.companies.search(is_demo=True)) == 1, "reloading replaces the demo company instead of doubling it"
ok(call("demo_remove"))
assert not T.companies.search(is_demo=True) and M["DemoData"].state() == "removed"
as_user(None)
bad(call("careers_page", "larkspur"))
assert M["DemoData"].state() == "removed", "removed demo data doesn't come back by itself"

# ---------------------------------------------------------------------------------- workspace: create, sample, invite, join
hr = person("hr@example.com", "Harriet Ross")
eve = person("eve@example.com", "Eve Stone")
mal = person("mal@example.com", "Mallory Outsider")
assert denied("get_home"), "guests can't open the dashboard"
as_user(hr)
assert call("get_me")["company"] is None
assert denied("list_people"), "no company yet"
bad(call("create_company", " "))
co = ok(call("create_company", "Acme Robotics", "Canada", "CAD", "Head of People", True))["company"]
bad(call("create_company", "Again"), "one company per account")
me = call("get_me")
assert me["company"] == "Acme Robotics" and me["role"] == "admin" and me["has_sample"]
ppl = call("list_people")
assert len(ppl["people"]) >= 25 and ppl["can_add"]
assert any(p["name"].startswith("Bart ") for p in ppl["people"]), "preferred names are used"
home = call("get_home")
assert home["is_admin"] and home["stats"]["headcount"] > 10 and home["needs"], "sample gives the HR lead things to do"
kinds = {n["kind"] for n in home["needs"]}
assert {"approval", "review", "survey"} <= kinds, kinds
priya = [p for p in ppl["people"] if p["name"] == "Priya Raman"][0]
inv = ok(call("invite_code", priya["id"]))
as_user(mal)
bad(call("join_company", "wrong-code"))
as_user(eve)
ok(call("join_company", inv["code"]))
bad(call("join_company", inv["code"]), "already in a company")
me_eve = call("get_me")
assert me_eve["company"] == "Acme Robotics" and me_eve["role"] == "employee" and me_eve["emp_name"] == "Priya Raman"
as_user(mal)
assert denied("list_people")

# ---------------------------------------------------------------------------------- people: permissions on one profile
as_user(eve)
lena = [p for p in ppl["people"] if p["name"] == "Lena Fischer"][0]
kwame = [p for p in ppl["people"] if p["name"] == "Kwame Mensah"][0]
other = ok(call("get_person", lena["id"]))["person"]
assert "pay_rate" not in other and "phone" not in other and "hr_notes" not in other and not other["history"], "colleagues see no private fields"
mine = ok(call("get_person", priya["id"]))["person"]
assert mine["can_private"] and "pay_rate" in mine and "hr_notes" not in mine and mine["balances"]
bad(call("update_person", lena["id"], "personal", {"phone": "1"}), "can't edit a colleague")
ok(call("update_person", priya["id"], "personal", {"phone": "+1 514 555 0199", "pronouns": "she/her"}))
bad(call("update_person", priya["id"], "pay", {"pay_rate": 999999}), "can't give yourself a raise")
bad(call("update_person", priya["id"], "personal", {"first_name": ""}))
assert denied("add_person", {"first_name": "X"})
as_user(hr)
lena_full = ok(call("get_person", lena["id"]))["person"]
assert "pay_rate" in lena_full and "hr_notes" in lena_full
r = ok(call("update_person", kwame["id"], "pay", {"pay_rate": "150000"}, "2026-12-01"))
assert r["changed"] == 1 and r["person"]["pay_rate"] == 150000
assert T.changes.search(field="Pay rate", new="150000")[0]["effective"].isoformat() == "2026-12-01"
bad(call("update_person", kwame["id"], "pay", {"pay_rate": "lots"}))
bad(call("update_person", lena["id"], "job", {"manager": kwame["id"]}), "no loops in the reporting line")
as_user(eve)
kw = ok(call("get_person", kwame["id"]))["person"]
assert "pay_rate" not in kw
as_user(hr)
newbie = ok(call("add_person", {"first_name": "Zed", "last_name": "Newman", "work_email": "zed@acme.example",
                                "title": "Engineer", "start_date": "2099-01-04", "manager": lena["id"]}))["person"]
assert newbie["status"] == "onboarding"
bad(call("add_person", {"first_name": "Dup", "work_email": "zed@acme.example"}), "emails are unique per company")
bad(call("add_person", {"first_name": ""}))
prev = ok(call("import_people", "First name,Last name,Email,Title,Manager email\nAda,Byron,ada@acme.example,Analyst,zed@acme.example\n,NoFirst,x@y.z,Thing,\nBad,Mail,not-an-email,X,", False))
assert prev["total"] == 3 and prev["problems"] == 2
imp = ok(call("import_people", "First name,Last name,Email,Title,Manager email\nAda,Byron,ada@acme.example,Analyst,zed@acme.example\n", True))
assert imp["added"] == 1 and T.employees.get(work_email="ada@acme.example")["manager"]["first_name"] == "Zed"
bad(call("import_people", "Foo,Bar\n1,2"), "needs a name column")
org = call("org_chart")
assert len(org["nodes"]) >= 25 and org["open_roles"]
marc = [p for p in ppl["people"] if p["name"] == "Marc Lefebvre"][0]
bad(call("terminate", marc["id"], {}), "needs a last day")
t = ok(call("terminate", newbie["id"], {"end_date": "2099-03-01", "reason": "Resignation", "regretted": False}))
assert t["person"]["status"] == "onboarding", "a future last day doesn't end employment yet"
me_row = T.employees.get(user=hr)
bad(call("terminate", me_row.get_id(), {"end_date": "2026-01-01"}), "can't offboard yourself")
ok(call("set_status", lena["id"], "leave"))
ok(call("set_status", lena["id"], "active"))
bad(call("set_status", lena["id"], "terminated"))
asset = ok(call("save_asset", kwame["id"], {"kind": "Laptop", "name": "Dell XPS", "serial": "X1"}))["asset"]
assert ok(call("return_asset", asset["id"]))["asset"]["returned"]
assert len(call("audit_log")["items"]) > 5

# ---------------------------------------------------------------------------------- view as
as_user(eve)
bad(call("view_as", lena["id"]), "only real HR admins can preview")
as_user(hr)
ok(call("view_as", priya["id"]))
assert call("get_me")["viewing_as"] == "Priya Raman" and call("get_me")["role"] == "employee"
assert denied("audit_log"), "previewing as an employee really has employee rights"
ok(call("view_as", None))
assert call("get_me")["viewing_as"] is None

# ---------------------------------------------------------------------------------- time off
as_user(eve)
ov = call("timeoff_overview")
vac = [t for t in ov["types"] if t["name"] == "Vacation"][0]
unpaid = [t for t in ov["types"] if t["name"] == "Unpaid"][0]
assert not ov["approvals"], "an employee has nothing to approve"
bad(call("request_time_off", vac["id"], "2099-06-10", "2099-06-01"), "end before start")
bad(call("request_time_off", vac["id"], "2099-06-06", "2099-06-07"), "a weekend is 0 days")
bad(call("request_time_off", vac["id"], "2099-06-01", "2099-08-30"), "more than the allowance")
rq = ok(call("request_time_off", vac["id"], "2099-06-01", "2099-06-05", "Beach"))["request"]
assert rq["days"] == 5 and rq["status"] == "pending"
bad(call("request_time_off", vac["id"], "2099-06-03", "2099-06-04"), "overlaps")
ok(call("request_time_off", unpaid["id"], "2099-07-01", "2099-08-30"), "no limit on unpaid")
assert call("count_days", "2026-12-21", "2026-12-27") == 4, "Christmas Day is a holiday (Boxing Day 2026 is a Saturday)"
bad(call("decide_request", rq["id"], True), "can't approve your own")
as_user(hr)
appr = call("timeoff_overview")["approvals"]
assert any(a["id"] == rq["id"] for a in appr)
ok(call("decide_request", rq["id"], True, "Enjoy"))
bad(call("decide_request", rq["id"], False), "already answered")
assert denied("save_holiday", "X", "2026-01-01") is False
bad(call("save_holiday", "Dup", "2026-12-25"), "one holiday per day")
lt = ok(call("save_leave_type", None, "Volunteering", 2, True, "sky"))["type"]
ok(call("delete_leave_type", lt["id"]))
bad(call("delete_leave_type", vac["id"]), "used types can't be deleted")
as_user(eve)
assert denied("save_leave_type", None, "X", 1)
ok(call("cancel_request", rq["id"]))
out = call("timeoff_overview", "2026-01-01")["out"]
assert isinstance(out, list)

# ---------------------------------------------------------------------------------- hiring
as_user(eve)
hv = call("hiring_overview")
assert not hv["jobs"] and hv["open_roles"], "employees see open roles, not candidates"
as_user(hr)
hv = call("hiring_overview")
j = [x for x in hv["jobs"] if x["counts"]["applied"]][0]
assert j["counts"]["applied"] >= 1
board = ok(call("get_job", j["id"]))
assert len(board["columns"]) == 6
cand = board["columns"][0]["candidates"][0]
as_user(eve)
bad(call("get_job", j["id"]))
bad(call("get_candidate", cand["id"]))
as_user(hr)
assert ok(call("get_candidate", cand["id"]))["candidate"]["cover"] is not None
ok(call("move_candidate", cand["id"], "interview"))
bad(call("move_candidate", cand["id"], "hired"), "use Hire")
ok(call("rate_candidate", cand["id"], 4))
assert ok(call("add_note", cand["id"], "Great call"))["candidate"]["notes"][0]["text"] == "Great call"
bad(call("add_note", cand["id"], " "))
hired = ok(call("hire_candidate", cand["id"], "2099-02-01"))
assert hired["employee"]["status"] == "onboarding"
assert T.checklists.get(employee=T.employees.get_by_id(hired["employee"]["id"]), kind="onboarding") is not None
bad(call("hire_candidate", cand["id"], "2099-02-01"), "already hired")
nj = ok(call("save_job", None, {"title": "Chief Snack Officer", "status": "open", "department": "Operations"}))["job"]
ok(call("add_candidate", nj["id"], {"name": "Sam Snack", "source": "Referral"}))
bad(call("save_job", None, {"title": ""}))
assert ok(call("careers_page", co["slug"]))["jobs"], "the company's own careers page lists open jobs"

# ---------------------------------------------------------------------------------- onboarding
ob = call("onboarding_overview")
assert ob["open"] and ob["my_tasks"]
cl = ok(call("get_checklist", ob["open"][0]["id"]))
task = cl["tasks"][0]
assert ok(call("tick_task", task["id"], True))["task"]["done"]
assert not ok(call("tick_task", task["id"], False))["task"]["done"]
ok(call("add_task", ob["open"][0]["id"], "Book a team lunch", "manager", "2099-01-10"))
bad(call("add_task", ob["open"][0]["id"], " "))
as_user(eve)
bad(call("tick_task", task["id"], True), "HR tasks are for HR")
bad(call("get_checklist", ob["open"][0]["id"]), "not someone else's checklist")

# ---------------------------------------------------------------------------------- performance, kudos, pulse
pv = call("performance_overview")
assert pv["to_write"] and pv["kudos"] and pv["survey"]
rv = pv["to_write"][0]
bad(call("save_review", rv["id"], {"0": "Good"}, 0, True), "needs a rating to submit")
ok(call("save_review", rv["id"], {"0": "Good year"}, 0, False))
ok(call("save_review", rv["id"], {"0": "Good year"}, 4, True))
assert ok(call("get_review", rv["id"]))["editable"]
ok(call("give_kudos", lena["id"], "Be kind", "Thanks for the help!"))
bad(call("give_kudos", priya["id"], "Be kind", "Me me me"), "no self-kudos")
g = ok(call("save_goal", None, None, "Learn Spanish", "2099-01-01", 10))["goal"]
ok(call("save_goal", g["id"], None, "Learn Spanish", "2099-01-01", 100))
assert T.goals.get_by_id(g["id"])["status"] == "done"
bad(call("save_goal", None, lena["id"], "Lena's goal"), "can't set a colleague's goal")
ok(call("answer_survey", pv["survey"]["id"], 9, "Nice place"))
bad(call("answer_survey", pv["survey"]["id"], 9), "one answer each")
assert not T.survey_answers.search(comment="Nice place")[0]["survey"] is None
assert "employee" not in [c["name"] for c in T.survey_answers.list_columns()], "answers are anonymous"
assert denied("start_cycle", "X")
as_user(hr)
cyc = call("performance_overview")["cycles"][0]
st = ok(call("cycle_status", cyc["id"]))
assert st["rows"] and "1" in st["distribution"]
new_cycle = ok(call("start_cycle", "Spring reviews"))
assert new_cycle["reviews"] > 20
ok(call("close_cycle", new_cycle["cycle"]["id"]))
sv = ok(call("start_survey", ""))["survey"]
assert not sv["visible"], "results stay hidden under 3 answers"
ok(call("view_as", priya["id"]))
bad(call("answer_survey", sv["id"], 5), "no anonymous answers while previewing")
ok(call("view_as", None))

# ---------------------------------------------------------------------------------- policies, announcements
dv = call("docs_overview")
pol = [p for p in dv["policies"] if p["require_ack"]][0]
ok(call("acknowledge", pol["id"]))
assert ok(call("get_policy", pol["id"]))["policy"]["acked"]
np_ = ok(call("save_policy", None, "Pets at work", "Dogs are welcome on Fridays.", True))["policy"]
ok(call("save_policy", np_["id"], "Pets at work", "Dogs and cats are welcome on Fridays.", True))
bad(call("save_policy", None, "X", "short"))
ok(call("post_announcement", "Pizza Friday", "In the kitchen at noon", True))
assert call("docs_overview")["announcements"][0]["title"] == "Pizza Friday", "pinned first"
as_user(eve)
assert denied("post_announcement", "Hack", "x")
assert ok(call("get_policy", np_["id"]))["policy"]["acked"] is False

# ---------------------------------------------------------------------------------- reports, export, settings
assert denied("get_reports")
as_user(hr)
rep = call("get_reports")
assert rep["headcount"] > 10 and len(rep["trend"]) == 12 and rep["by_department"]
csvp = ok(call("export_people_csv", True))
assert csvp["csv"].startswith("First name") and "Pay rate" in csvp["csv"]
pay = ok(call("payroll_export", "2099-06-01", "2099-06-30"))
assert pay["count"] > 10
bad(call("payroll_export", "2099-06-30", "2099-06-01"))
exp = ok(call("export_company"))
assert '"employees"' in exp["json"] and "invite_code" not in exp["json"]
ok(call("save_list", "departments", ["Leadership", "People", "Engineering", "Design", "Sales", "Operations", "Legal"]))
bad(call("save_list", "departments", []))
ok(call("save_list", "onboarding", [{"title": "Say hello", "role": "manager", "day": 0}, {"title": ""}]))
assert call("get_company")["onboarding"] == [{"title": "Say hello", "role": "manager", "day": 0}]
bad(call("save_list", "nonsense", ["x"]))
ok(call("save_company", "Acme Robotics Inc.", "Canada", "USD"))
n_before = len(T.employees.search(company=T.companies.get(slug=co["slug"])))
rem = ok(call("remove_sample"))
assert rem["removed"] > 100
left = T.employees.search(company=T.companies.get(slug=co["slug"]))
assert all(not e["is_demo"] for e in left) and len(left) < n_before
assert T.employees.get(user=eve) is None or not T.employees.get(user=eve)["is_demo"]
call("get_home"); call("list_people"); call("timeoff_overview"); call("performance_overview"); call("get_reports")

# ---------------------------------------------------------------------------------- Privacy & Terms
if "legal_server" in M:
    as_user(ana)
    st = call("legal_state")
    assert st["signedIn"] and st["accepted_version"] is None
    ok(call("legal_accept", st["version"], "signup"))
    assert ana["legal_source"] == "signup" and call("legal_state")["accepted_version"] == st["version"]

# ---------------------------------------------------------------------------------- schema check (App Board): names only, never data
r = anvil.server.ENDPOINTS["/schema-check"](tables="users, employees,no_such_table")
json.dumps(r)
assert "email" in r["tables"]["users"] and "title" in r["tables"]["employees"] and r["tables"]["no_such_table"] is None, r

# ---------------------------------------------------------------------------------- every callable is covered by a permission check
# A callable that changes data without require_user / a C.require_* check is a security hole. List the public ones here.
PUBLIC = {"log_client_error", "get_me", "session_ping", "submit_feedback", "legal_state", "legal_accept",
          "careers_page", "apply_to_job"}
for name, (f, need) in sorted(anvil.server.CALLABLES.items()):
    if name in PUBLIC:
        continue
    assert need, "%s is callable by anyone: add require_user=True (or list it in PUBLIC in test_server.py)" % name

print("ALL OK (%d server functions)" % len(anvil.server.CALLABLES))
