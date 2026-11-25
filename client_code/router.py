"""Page addresses: #name/arg1/arg2 -> a page Form (open_form), with sign-in rules.

Links in templates are plain <a href="#home">; code calls router.go("person", id).

    PAGES[name] = (who may open it, browser-tab title)
      who: None = anyone, "guest" = signed out only, "user" = signed in, "member" = signed in AND in a company
      (signed-in people without a company go to #setup), "admin" = the site admin (not company HR)
    NAV = the header menu (members); TABS = the phone tab bar (at most 4). (page, label, icon)
New page: add it to PAGES and to _form().
"""
import anvil
import anvil.js
from anvil.js import window

from . import state

PAGES = {
    "landing": (None, "HR for small teams"),
    "auth": ("guest", "Sign in"),
    "careers": (None, "Careers"),
    "setup": ("user", "Set up your company"),
    "join": ("user", "Join your company"),
    "home": ("member", "Home"),
    "people": ("member", "People"),
    "person": ("member", "Profile"),
    "org": ("member", "Org chart"),
    "timeoff": ("member", "Time off"),
    "hiring": ("member", "Hiring"),
    "job": ("member", "Job pipeline"),
    "onboarding": ("member", "Onboarding"),
    "checklist": ("member", "Checklist"),
    "performance": ("member", "Performance"),
    "review": ("member", "Review"),
    "cycle": ("member", "Review cycle"),
    "docs": ("member", "Policies and news"),
    "policy": ("member", "Policy"),
    "reports": ("member", "Reports"),
    "settings": ("member", "Settings"),
    "more": ("member", "Everything"),
    "profile": ("user", "Your account"),
    "admin": ("admin", "Site admin"),
}
NAV = [("home", "Home", "home"), ("people", "People", "users"), ("timeoff", "Time off", "calendar"),
       ("hiring", "Hiring", "briefcase"), ("performance", "Performance", "target"), ("more", "More", "grid")]
TABS = [("home", "Home", "home"), ("people", "People", "users"), ("timeoff", "Time off", "calendar"),
        ("more", "More", "grid")]
APP_NAME = "HR Platform"
_r: dict = {"after": "", "listening": False}

# page -> the menu item it belongs to (so "Job pipeline" lights up Hiring)
SECTION = {"person": "people", "org": "people", "job": "hiring", "checklist": "more", "onboarding": "more",
           "review": "performance", "cycle": "performance", "docs": "more", "policy": "more", "reports": "more",
           "settings": "more"}


def _form(name):
    """The page's Form class (imported when first needed, so start-up stays quick)."""
    if name == "landing":
        from .Pages.Landing import Landing
        return Landing
    if name == "auth":
        from .Pages.Auth import Auth
        return Auth
    if name == "careers":
        from .Pages.Careers import Careers
        return Careers
    if name in ("setup", "join"):
        from .Pages.Setup import Setup
        return Setup
    if name == "home":
        from .Pages.Home import Home
        return Home
    if name == "people":
        from .Pages.People import People
        return People
    if name == "person":
        from .Pages.Person import Person
        return Person
    if name == "org":
        from .Pages.Org import Org
        return Org
    if name == "timeoff":
        from .Pages.TimeOff import TimeOff
        return TimeOff
    if name == "hiring":
        from .Pages.Hiring import Hiring
        return Hiring
    if name == "job":
        from .Pages.Job import Job
        return Job
    if name == "onboarding":
        from .Pages.Onboarding import Onboarding
        return Onboarding
    if name == "checklist":
        from .Pages.Checklist import Checklist
        return Checklist
    if name == "performance":
        from .Pages.Performance import Performance
        return Performance
    if name == "review":
        from .Pages.Review import Review
        return Review
    if name == "cycle":
        from .Pages.Cycle import Cycle
        return Cycle
    if name == "docs":
        from .Pages.Docs import Docs
        return Docs
    if name == "policy":
        from .Pages.Policy import Policy
        return Policy
    if name == "reports":
        from .Pages.Reports import Reports
        return Reports
    if name == "settings":
        from .Pages.Settings import Settings
        return Settings
    if name == "more":
        from .Pages.More import More
        return More
    if name == "profile":
        from .Pages.Profile import Profile
        return Profile
    from .Pages.Admin import Admin
    return Admin


def parse(hash_text):
    h = (hash_text or "").lstrip("#").lstrip("!").lstrip("/").split("?")[0]
    parts = [window.decodeURIComponent(p) for p in h.split("/") if p]
    return (parts[0] if parts else ""), parts[1:]


def href(name, *args):
    """'#name/arg1/arg2' with every part URL-encoded (row ids contain brackets and commas)."""
    return "#" + "/".join([name] + [window.encodeURIComponent(str(a)) for a in args if a not in (None, "")])


def home_page():
    if not state.me():
        return "landing"
    return "home" if state.in_company() else "setup"


def show():
    """Open the page for the current address."""
    name, args = parse(window.location.hash)
    if name not in PAGES:
        name, args = home_page(), []
    who = PAGES[name][0]
    if who == "guest" and state.me():
        name, args = home_page(), []
    elif who in ("user", "member", "admin") and not state.me():
        _r["after"] = window.location.hash
        name, args = "auth", []
    elif who == "member" and not state.in_company():
        name, args = "setup", []
    elif who == "admin" and not state.is_admin():
        state.toast("That page is for site admins only.", "error")
        name, args = home_page(), []
    if name in ("setup", "join") and state.in_company():
        name, args = "home", []
    window.document.title = PAGES[name][1] + " · " + APP_NAME
    window.UI_READY = False
    page = _form(name)(args=(["join"] + list(args)) if name == "join" else args)
    anvil.open_form(page)
    shell = getattr(page, "layout", None)
    if shell is not None and hasattr(shell, "refresh"):
        shell.refresh(SECTION.get(name, name))  # the layout is reused between pages: redraw who/where
    window.scrollTo(0, 0)
    if not getattr(page, "waits", False):
        window.UI_READY = True  # tests and screenshots wait for this


def go(name, *args):
    """Go to a page. Same address again = reload the page."""
    target = href(name, *args)
    if window.location.hash == target:
        show()
    else:
        window.location.hash = target


def replace(name, *args):
    """Change the address without opening anything (a page that switches its own view)."""
    window.history.replaceState(None, "", href(name, *args))


def after_sign_in():
    """Where to go once someone signs in: the page they were heading for, or home."""
    target = _r["after"]
    _r["after"] = ""
    if target and target != window.location.hash:
        window.location.hash = target
    else:
        go(home_page())


def remember_after(target):
    _r["after"] = target


def _on_hash(event):
    show()


def _on_click(event):
    """Anvil puts a <base href> in the page: a plain #link would reload the app when the address has a query."""
    t = event.target
    a = t.closest("a[href^='#']") if getattr(t, "closest", None) else None
    if a is None or event.defaultPrevented or event.ctrlKey or event.metaKey or a.getAttribute("target"):
        return
    event.preventDefault()
    target = a.getAttribute("href")
    if window.location.hash == target:
        show()
    else:
        window.location.hash = target


def start():
    if not _r["listening"]:
        window.addEventListener("hashchange", anvil.js.report_exceptions(_on_hash))
        window.document.addEventListener("click", anvil.js.report_exceptions(_on_click))
        _r["listening"] = True
    show()
