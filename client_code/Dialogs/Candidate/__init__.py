import datetime

import anvil.server
from anvil import *

from ._anvil_designer import CandidateTemplate
from ... import router, state

MOVABLE = ["applied", "screen", "interview", "offer", "rejected"]


class Candidate(CandidateTemplate):
    """A candidate's full details: contact, cover letter, rating (1-5), stage, notes timeline and, for HR, Hire
    (start date + optional title -> their profile and onboarding checklist). The board reloads when it closes."""

    def __init__(self, cand_id=None, **properties):
        super().__init__(**properties)
        self._id = cand_id
        self._c: dict = {}
        self._labels: dict = {}
        self._stars = [self.r1, self.r2, self.r3, self.r4, self.r5]
        for i, b in enumerate(self._stars):
            state.set_control_attr(b, "aria-label", "%d out of 5" % (i + 1))
        self.hire_part.visible = False
        state.set_control_attr(self.start_box, "type", "date")
        state.live(self.hired_text)
        r = anvil.server.call("get_candidate", cand_id)
        if not r.get("ok"):
            self.body_part.visible = False
            self.hired_box.visible = False
            self.message.text, self.message.visible = r.get("error") or "That candidate isn't available.", True
            return
        self._labels = r.get("stage_labels") or {}
        self._draw(r["candidate"])

    # ---- drawing
    def _draw(self, c):
        self._c = c
        hired = bool(c.get("employee_id"))
        self.av.initials, self.av.tone = c.get("initials") or "?", c.get("tone") or 0
        self.name.text = c["name"]
        state.heading(self.name, 2)
        self.job_line.text = c.get("job") or ""
        self.stage_badge.text = c.get("stage_label") or ""
        self.stage_badge.role = ["badge", "badge-good" if hired else ("badge-bad" if c["stage"] == "rejected"
                                                                     else "badge-brand")]
        email = c.get("email") or ""
        self.email_link.text, self.email_link.url = email, ("mailto:" + email) if email else ""
        self.email_link.visible, self.email_none.visible = bool(email), not email
        self.phone.text = c.get("phone") or "Not given"
        link = c.get("link") or ""
        if link and not link.startswith("http"):
            link = "https://" + link
        self.web_link.text, self.web_link.url = c.get("link") or "", link
        self.web_link.visible, self.web_none.visible = bool(link), not link
        if link:
            state.set_attr(self.web_link, "target", "_blank")
            state.set_attr(self.web_link, "rel", "noopener noreferrer")
        self.source.text = c.get("source") or "Added by hand"
        self.applied.text = state.fmt_date(c.get("created")) + " (" + state.ago(c.get("created")) + ")"
        self.cover.text = c.get("cover") or ""
        self.cover_part.visible = bool(c.get("cover"))
        self._draw_rating(c.get("rating") or 0)
        # stage + hire
        self.stage_part.visible = not hired
        if not hired:
            self.stage_box.items = [(self._labels.get(s, s.capitalize()), s) for s in MOVABLE]
            self.stage_box.selected_value = c["stage"] if c["stage"] in MOVABLE else "applied"
        self.hired_box.visible = hired
        if hired:
            first = c["name"].split(" ")[0]
            self.hired_text.text = "%s is hired. Their onboarding checklist is ready." % first
            state.set_attr(self.profile_link, "href", router.href("person", c["employee_id"]))
            self.hire_part.visible = False
        self.hire_button.visible = state.is_hr() and not hired and not self.hire_part.visible
        if "notes" in c:
            self.notes_panel.items = c["notes"]
            self.no_notes.visible = not c["notes"]

    def _draw_rating(self, rating):
        for i, b in enumerate(self._stars):
            on = i + 1 == rating
            b.role = ["seg", "on"] if on else ["seg"]
            state.set_control_attr(b, "aria-pressed", "true" if on else "false")
        self.rate_hint.text = ("Rated %d out of 5" % rating) if rating else "Not rated yet"

    # ---- rating
    def _rate(self, n):
        r = anvil.server.call("rate_candidate", self._id, n)
        if not r.get("ok"):
            state.toast(r.get("error") or "That didn't save.", "error")
            return
        self._c["rating"] = r["candidate"]["rating"]
        self._draw_rating(self._c["rating"])
        state.focus(self._stars[n - 1])
        state.toast("Rated %d out of 5" % n, "ok")

    @handle("r1", "click")
    def r1_click(self, **event_args):
        self._rate(1)

    @handle("r2", "click")
    def r2_click(self, **event_args):
        self._rate(2)

    @handle("r3", "click")
    def r3_click(self, **event_args):
        self._rate(3)

    @handle("r4", "click")
    def r4_click(self, **event_args):
        self._rate(4)

    @handle("r5", "click")
    def r5_click(self, **event_args):
        self._rate(5)

    # ---- stage
    @handle("move_button", "click")
    def move_button_click(self, **event_args):
        stage = self.stage_box.selected_value
        if stage == self._c.get("stage"):
            state.toast("%s is already in %s." % (self._c["name"].split(" ")[0], self._labels.get(stage, stage)))
            return
        self.move_button.enabled = False
        try:
            r = anvil.server.call("move_candidate", self._id, stage)
        finally:
            self.move_button.enabled = True
        if not r.get("ok"):
            state.toast(r.get("error") or "Can't move that candidate.", "error")
            return
        self._reload()
        state.toast("Moved to %s" % self._labels.get(stage, stage), "ok")

    def _reload(self):
        r = anvil.server.call("get_candidate", self._id)
        if r.get("ok"):
            self._draw(r["candidate"])

    # ---- notes
    @handle("note_button", "click")
    def note_button_click(self, **event_args):
        text = (self.note_box.text or "").strip()
        if not text:
            state.toast("Write the note first.", "error")
            self.note_box.focus()
            return
        self.note_button.enabled, self.note_button.text = False, "Adding..."
        try:
            r = anvil.server.call("add_note", self._id, text)
        finally:
            self.note_button.enabled, self.note_button.text = True, "Add note"
        if not r.get("ok"):
            state.toast(r.get("error") or "That didn't save.", "error")
            return
        self.note_box.text = ""
        self._draw(r["candidate"])
        state.toast("Note added", "ok")
        self.note_box.focus()

    # ---- hire
    @handle("hire_button", "click")
    def hire_button_click(self, **event_args):
        self.hire_part.visible = True
        self.hire_button.visible = False
        if not self.start_box.text:
            self.start_box.text = (datetime.date.today() + datetime.timedelta(days=14)).isoformat()
        self.hire_title_box.placeholder = self._c.get("job") or "Same as the job"
        self.start_box.focus()

    @handle("hire_cancel_button", "click")
    def hire_cancel_button_click(self, **event_args):
        self.hire_part.visible = False
        self.hire_message.visible = False
        self.hire_button.visible = True
        state.focus(self.hire_button)

    @handle("hire_confirm_button", "click")
    def hire_confirm_button_click(self, **event_args):
        start = (self.start_box.text or "").strip()
        if len(start) != 10:
            self.hire_message.text, self.hire_message.visible = "Choose their start date.", True
            self.start_box.focus()
            return
        self.hire_message.visible = False
        self.hire_confirm_button.enabled, self.hire_confirm_button.text = False, "Hiring..."
        try:
            r = anvil.server.call("hire_candidate", self._id, start, (self.hire_title_box.text or "").strip())
        finally:
            self.hire_confirm_button.enabled, self.hire_confirm_button.text = True, "Confirm hire"
        if not r.get("ok"):
            self.hire_message.text, self.hire_message.visible = r.get("error") or "That didn't work.", True
            if "already hired" in (r.get("error") or ""):
                self._reload()
            return
        self.hire_part.visible = False
        first = self._c["name"].split(" ")[0]
        state.toast("%s is hired: onboarding checklist created" % first, "ok")
        self._reload()
        state.focus(self.close_button)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=True)
