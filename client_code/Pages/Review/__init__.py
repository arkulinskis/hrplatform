import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import ReviewTemplate
from ... import router, state

RATINGS = {1: "Needs improvement", 2: "Developing", 3: "Solid", 4: "Strong", 5: "Outstanding"}


class Review(ReviewTemplate):
    """#review/<id>: write (or read) one review: who it's about, the cycle and due date, their goals for context,
    each question, an overall rating 1-5. Save draft / Submit (asks first). Read-only once submitted or closed."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._id = args[0] if args else None
        self._rating = [0]
        self._editable = [False]
        self._buttons = [(self.r1, 1), (self.r2, 2), (self.r3, 3), (self.r4, 4), (self.r5, 5)]
        for btn, n in self._buttons:
            btn.add_event_handler("click", self._rate_handler(n))
        state.heading(self.title_label, 1)
        self._load()

    def _load(self):
        r: dict = {"ok": False}
        if self._id:
            r = anvil.server.call("get_review", self._id)
        ok = bool(r.get("ok"))
        self.missing_box.visible = not ok
        self.main_box.visible = ok
        if not ok:
            self.missing_text.text = r.get("error") or "The link may be old, or the review belongs to someone else."
            return
        rev = r["review"]
        editable = bool(r.get("editable")) and rev["status"] != "submitted"
        self._editable[0] = editable
        self.title_label.text = rev["label"]
        self.av.initials, self.av.tone = rev["initials"], rev["tone"]
        bits = [rev["cycle"]] if rev.get("cycle") else []
        if rev["kind"] == "manager":
            bits.append("written by %s" % rev["reviewer"])
        if rev.get("due"):
            bits.append("due " + state.fmt_date(rev["due"]))
        self.meta.text = " · ".join(bits)
        submitted = rev["status"] == "submitted"
        self.status.text = "Submitted" if submitted else "Draft"
        self.status.role = ["badge", "badge-good"] if submitted else ["badge", "badge-warn"]
        if not editable:
            self.readonly_note.visible = True
            if submitted:
                self.readonly_note.text = "Submitted on %s. This is the final version." % state.fmt_date(rev["submitted_at"])
            else:
                self.readonly_note.text = "This review cycle is closed, so the review can't be changed."
        qs = r["questions"]
        answers = r.get("answers") or {}
        self.questions_panel.items = [{"key": str(i), "n": i + 1, "question": q, "answer": answers.get(str(i), ""),
                                       "editable": editable} for i, q in enumerate(qs)]
        self._rating[0] = rev.get("rating") or 0
        self.rating_edit.visible = editable
        self.rating_text.visible = not editable
        if editable:
            self._mark()
        else:
            n = self._rating[0]
            self.rating_text.text = ("%d of 5: %s" % (n, RATINGS[n])) if n in RATINGS else "No rating given."
        self.actions.visible = editable
        goals = [dict(g, can_edit=False) for g in (r.get("goals") or [])]
        self.goals_panel.items = goals
        self.no_goals.visible = not goals

    def _rate_handler(self, n):
        def handler(**event_args):
            self._rating[0] = n
            self._mark()
        return handler

    def _mark(self):
        for btn, n in self._buttons:
            on = n == self._rating[0]
            btn.role = ["seg", "on"] if on else ["seg"]
            state.set_control_attr(btn, "aria-pressed", "true" if on else "false")

    def _answers(self):
        out = {}
        for c in self.questions_panel.get_components():
            fn = getattr(c, "value", None)
            if callable(fn):
                k, v = fn()
                out[k] = v
        return out

    def _save(self, submit):
        btn = self.submit_button if submit else self.save_button
        roles = list(btn.role) if isinstance(btn.role, list) else ([btn.role] if btn.role else [])
        btn.role, btn.enabled = roles + ["btn-is-busy"], False
        try:
            r = state.call("save_review", self._id, self._answers(), self._rating[0], submit)
        finally:
            btn.role, btn.enabled = roles, True
        return r

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        if self._save(False) is not None:
            state.toast("Draft saved. Only you can see it until you submit.", "ok")

    @handle("submit_button", "click")
    def submit_button_click(self, **event_args):
        if self._rating[0] < 1:
            state.toast("Choose an overall rating before you submit.", "error")
            state.focus(self.r3)
            return
        if not any((v or "").strip() for v in self._answers().values()):
            state.toast("Answer at least one question before you submit.", "error")
            return
        if not confirm("Once it's submitted you can't change it, and HR can read it straight away.",
                       title="Submit this review?", buttons=[("Keep editing", False), ("Submit review", True)],
                       role="app-dialog"):
            return
        if self._save(True) is not None:
            state.toast("Review submitted. Thank you!", "ok")
            self._load()
            window.scrollTo(0, 0)
