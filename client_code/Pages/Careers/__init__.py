import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import CareersTemplate
from ... import state
from ...Dialogs.Apply import Apply


class Careers(CareersTemplate):
    """#careers/<slug>: a company's public jobs page (no sign-in). Jobs open like an accordion; Apply opens the
    application form. No slug = the sample company "larkspur"."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._company = ""
        slug = args[0] if args else "larkspur"
        state.heading(self.title_label, 1)
        self.jobs_panel.add_event_handler("x-apply", self._apply)
        r = anvil.server.call("careers_page", slug)
        ok = bool(r.get("ok"))
        self.found_part.visible, self.missing_part.visible = ok, not ok
        if not ok:
            window.document.title = "Careers page not found"
            return
        self._company = r["company"]
        self.title_label.text = "Careers at %s" % self._company
        window.document.title = "Careers at %s" % self._company
        self.intro.text = ("We're %s: a small team that cares about good work and kind colleagues. If one of these "
                           "jobs sounds like you, tell us a little about yourself. No account needed." % self._company)
        self.demo_note.visible = bool(r.get("demo"))
        jobs = r.get("jobs") or []
        if len(jobs) == 1:
            jobs[0]["open"] = True
        self.jobs_panel.items = jobs
        self.no_jobs.visible = not jobs
        self.count.text = state.plural(len(jobs), "open job") if jobs else "Open jobs"

    def _apply(self, job=None, **event_args):
        if job:
            alert(Apply(job=job, company=self._company), buttons=[], role="app-dialog", large=True)
