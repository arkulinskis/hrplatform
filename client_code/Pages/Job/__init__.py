import anvil.server
from anvil import *

from ._anvil_designer import JobTemplate
from ... import router, state
from ...Dialogs.AddCandidate import AddCandidate
from ...Dialogs.Candidate import Candidate
from ...Dialogs.JobEdit import JobEdit

STATUS = {"open": ("Open", "badge-good"), "draft": ("Draft", "badge-warn"), "closed": ("Closed", "")}
LABELS = {"applied": "Applied", "screen": "Phone screen", "interview": "Interview", "offer": "Offer",
          "hired": "Hired", "rejected": "Not moving on"}


class Job(JobTemplate):
    """#job/<id>: a job's header (status, edit, add candidate) and its pipeline board, one column per stage.
    Cards open the Candidate dialog; Next/Back move a candidate one stage."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._id = args[0] if args else None
        self._job: dict = {}
        self._sources: list = []
        state.heading(self.title_label, 1)
        self._seg = {"draft": self.s_draft, "open": self.s_open, "closed": self.s_closed}
        self.cols_panel.add_event_handler("x-open", self._open)
        self.cols_panel.add_event_handler("x-move", self._move)
        self._load()

    def _load(self):
        r: dict = anvil.server.call("get_job", self._id) if self._id else {"ok": False, "error": "No job was chosen."}
        ok = bool(r.get("ok"))
        self.found_part.visible, self.missing_part.visible = ok, not ok
        if not ok:
            self.missing_text.text = r.get("error") or "It may have been removed."
            return
        self._job, self._sources = r["job"], r.get("sources") or []
        self._draw_head()
        self.cols_panel.items = r["columns"]

    def _draw_head(self):
        j = self._job
        hr = state.is_hr()
        self.title_label.text = j["title"]
        bits = [b for b in (j.get("department"), j.get("location"), j.get("employment_type"), j.get("salary_range")) if b]
        if j.get("manager"):
            bits.append("Hiring manager: " + j["manager"])
        self.meta.text = " · ".join(bits)
        text, role = STATUS.get(j["status"], ("Draft", "badge-warn"))
        self.status_badge.text = text
        self.status_badge.role = ["badge"] + ([role] if role else [])
        self.status_badge.visible = not hr
        self.status_box.visible = hr
        for key, b in self._seg.items():
            b.role = ["seg", "on"] if key == j["status"] else ["seg"]
        self.edit_button.visible = hr
        self.add_button.visible = bool(j.get("can_manage"))
        counts = j.get("counts") or {}
        self.n_active.text, self.n_total.text = str(j.get("active", 0)), str(j.get("total", 0))
        self.n_hired.text = str(counts.get("hired", 0))
        self.desc.text = j.get("description") or "No description yet."
        self.careers_hint.text = {"open": "Shown on your public careers page.",
                                  "draft": "A draft: not on the careers page until you open it.",
                                  "closed": "Closed: no longer on the careers page."}.get(j["status"], "")

    # ---- status
    def _set_status(self, status):
        j = self._job
        if j.get("status") == status:
            return
        data = {"title": j["title"], "department": j.get("department"), "location": j.get("location"),
                "employment_type": j.get("employment_type"), "salary_range": j.get("salary_range"),
                "manager_id": j.get("manager_id"), "description": j.get("description"), "status": status}
        r = state.call("save_job", self._id, data)
        if r:
            self._job.update(r["job"])
            self._draw_head()
            state.focus(self._seg[status])
            state.toast({"open": "Open: now on the careers page", "draft": "Saved as a draft",
                         "closed": "Closed: off the careers page"}[status], "ok")

    @handle("s_draft", "click")
    def s_draft_click(self, **event_args):
        self._set_status("draft")

    @handle("s_open", "click")
    def s_open_click(self, **event_args):
        self._set_status("open")

    @handle("s_closed", "click")
    def s_closed_click(self, **event_args):
        self._set_status("closed")

    # ---- edit / add
    @handle("edit_button", "click")
    def edit_button_click(self, **event_args):
        meta = state.call("hiring_overview")
        if not meta:
            return
        job = alert(JobEdit(job=self._job, meta=meta), buttons=[], role="app-dialog", large=True)
        if job:
            state.toast("Job saved", "ok")
            self._job.update(job)
            self._draw_head()

    @handle("add_button", "click")
    def add_button_click(self, **event_args):
        c = alert(AddCandidate(job=self._job, sources=self._sources), buttons=[], role="app-dialog", large=True)
        if c:
            state.toast("%s added to Applied" % c["name"], "ok")
            self._load()

    # ---- board
    def _open(self, cand=None, **event_args):
        if not cand:
            return
        alert(Candidate(cand_id=cand["id"]), buttons=[], role="app-dialog", large=True)
        self._load()  # rating, notes, stage or a hire may have changed

    def _move(self, cand=None, stage=None, key=None, **event_args):
        if not cand or not stage:
            return
        r = state.call("move_candidate", cand["id"], stage)
        if not r:
            return
        self._load()
        state.refocus(self.cols_panel, key)
        if key and state.focus_key() != key:  # the card has no button of that kind any more (e.g. it reached Offer)
            state.refocus(self.cols_panel, "%s-%s" % (cand["id"], "back" if key.endswith("-next") else "next"))
        state.toast("%s moved to %s" % (cand["name"].split(" ")[0], LABELS.get(stage, stage)), "ok")
