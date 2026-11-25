from anvil import *
from anvil.js import window

from ._anvil_designer import HiringTemplate
from ... import router, state
from ...Dialogs.JobEdit import JobEdit

FILTERS = ["all", "open", "draft", "closed"]


class Hiring(HiringTemplate):
    """#hiring: HR and hiring managers see their jobs (pipeline counts per stage), new applications and the public
    careers page link. Everyone else sees the open roles, to refer friends."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._d: dict = {}
        self._filter = "all"
        self._url = ""
        self._seg = {"all": self.f_all, "open": self.f_open, "draft": self.f_draft, "closed": self.f_closed}
        self._load()

    def _load(self):
        d = state.call("hiring_overview")
        if not d:
            return
        self._d = d
        jobs, open_roles = d.get("jobs") or [], d.get("open_roles") or []
        hr = bool(d.get("can_create"))
        self.new_button.visible = hr
        has_jobs = hr or bool(jobs)
        if hr:
            self.lede.text = "Post jobs, move candidates through the stages and hire in one click: their profile and onboarding checklist are made for you."
        elif jobs:
            self.lede.text = "The jobs you're hiring for. Rate candidates, add notes and move them along; HR makes the final hire."
        else:
            self.lede.text = "Hiring is run by HR and the hiring managers. You can help by sending great people the careers page."
        # your jobs
        self.jobs_part.visible = has_jobs
        self.filter_box.visible = len(jobs) > 2
        self._draw_jobs()
        # open roles (people who don't manage them)
        slug = d.get("slug") or ""
        for j in open_roles:
            j["mode"], j["slug"] = "open", slug
        self.open_panel.items = open_roles
        self.no_open.visible = not open_roles
        self.open_part.visible = bool(open_roles) or not has_jobs
        # careers page link
        self._url = "%s%s%s" % (window.location.origin, window.location.pathname, router.href("careers", slug))
        state.set_attr(self.careers_link, "href", router.href("careers", slug))
        self.careers_url.text = self._url
        # new applications (HR)
        recent = d.get("recent") or []
        rows = [{"href": router.href("job", c["job_id"]), "name": c["name"], "initials": c["initials"],
                 "tone": c["tone"], "sub": "%s · %s" % (c["job"], state.ago(c["created"])),
                 "tag": c.get("source") or ""} for c in recent]
        self.recent_panel.items = rows
        self.no_recent.visible = not rows
        self.recent_part.visible = hr

    def _draw_jobs(self):
        jobs = self._d.get("jobs") or []
        shown = [j for j in jobs if self._filter == "all" or j["status"] == self._filter]
        self.jobs_panel.items = shown
        self.no_jobs.visible = not shown
        labels = {"all": "All", "open": "Open", "draft": "Drafts", "closed": "Closed"}
        for key in FILTERS:
            n = len(jobs) if key == "all" else len([j for j in jobs if j["status"] == key])
            self._seg[key].text = "%s (%d)" % (labels[key], n)
            self._seg[key].role = ["seg", "on"] if key == self._filter else ["seg"]
        if jobs and not shown:
            self.no_jobs_title.visible = False
            self.no_jobs_text.text = "No %s jobs." % labels[self._filter].lower().rstrip("s")
        else:
            self.no_jobs_title.visible = True
            self.no_jobs_text.text = ("Create your first job: as soon as it's open, it shows on your careers page and "
                                      "applications land in its pipeline.") if self._d.get("can_create") else \
                "No jobs are assigned to you."

    def _set_filter(self, value):
        self._filter = value
        self._draw_jobs()
        state.focus(self._seg[value])

    @handle("f_all", "click")
    def f_all_click(self, **event_args):
        self._set_filter("all")

    @handle("f_open", "click")
    def f_open_click(self, **event_args):
        self._set_filter("open")

    @handle("f_draft", "click")
    def f_draft_click(self, **event_args):
        self._set_filter("draft")

    @handle("f_closed", "click")
    def f_closed_click(self, **event_args):
        self._set_filter("closed")

    @handle("new_button", "click")
    def new_button_click(self, **event_args):
        job = alert(JobEdit(job=None, meta=self._d), buttons=[], role="app-dialog", large=True)
        if job:
            state.toast("%s created" % job["title"], "ok")
            router.go("job", job["id"])

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        if window.HR.copy(self._url):
            state.toast("Link copied", "ok")
        else:
            state.toast("Couldn't copy. Select the link and copy it instead.", "error")
