"""The public demo company "Larkspur Studio" (slug `larkspur`), so visitors can open a real careers page
(#careers/larkspur) before signing up. Loaded the first time anyone opens it (ensure_loaded); Admin -> Demo data
removes or reloads it, and a removal is remembered.

Every row belongs to a company flagged is_demo=True, so remove() deletes exactly that company and its rows.
(Each new workspace gets its own private sample data from Sample.py; that is separate and removed in Settings.)
"""
from anvil.tables import app_tables

from . import common as C

DEMO_NAME = "Larkspur Studio"
# Tables that hold demo rows (each has company + is_demo). Children before parents.
DEMO_TABLES = ["survey_done", "survey_answers", "surveys", "acks", "policies", "announcements", "kudos", "reviews",
               "review_cycles", "goals", "tasks", "checklists", "candidates", "jobs", "leave_requests", "assets",
               "files", "changes", "holidays", "leave_types", "employees"]


def state():
    return C.get_setting("demo", "never")  # "never" | "loaded" | "removed"


def ensure_loaded():
    if state() == "never":
        load()


def load():
    remove(remember=False)
    from . import Workspace, Sample
    company = Workspace.new_company(DEMO_NAME, "Canada", "CAD", demo=True)
    company["slug"] = "larkspur" if app_tables.companies.get(slug="larkspur") is None else company["slug"]
    Sample.seed(company, None)
    C.set_setting("demo", "loaded")
    return counts()


def _companies():
    return list(app_tables.companies.search(is_demo=True))


def remove(remember=True):
    for company in _companies():
        for name in DEMO_TABLES:
            for r in getattr(app_tables, name).search(company=company):
                r.delete()
        company.delete()
    if remember:
        C.set_setting("demo", "removed")
    return counts()


def counts():
    companies = _companies()
    out = {"companies": len(companies)}
    for name in ("employees", "jobs", "candidates"):
        out[name] = sum(len(getattr(app_tables, name).search(company=c)) for c in companies)
    return out
