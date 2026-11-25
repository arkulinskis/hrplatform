from anvil import *

from ._anvil_designer import PerformanceTemplate
from ... import router, state

TABS = ["reviews", "goals", "kudos", "pulse"]


def busy(btn, on):
    """Spinner + disabled while a button's server call runs (role btn-is-busy in app.css)."""
    roles = btn.role if isinstance(btn.role, list) else ([btn.role] if btn.role else [])
    roles = [r for r in roles if r != "btn-is-busy"]
    btn.role = roles + (["btn-is-busy"] if on else [])
    btn.enabled = not on


class Performance(PerformanceTemplate):
    """#performance/<tab>: reviews (to write, about me, HR's cycles), goals (mine + my team's), kudos, and the
    anonymous pulse survey (answer it; HR sees eNPS results). Each tab is its own address."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._tab = args[0] if args and args[0] in TABS else "reviews"
        self._d: dict = {}
        self._score = [-1]
        self._scale = [self.s0, self.s1, self.s2, self.s3, self.s4, self.s5, self.s6, self.s7, self.s8, self.s9,
                       self.s10]
        for n, b in enumerate(self._scale):
            b.add_event_handler("click", self._score_handler(n))
            state.set_control_attr(b, "aria-label", "%d out of 10" % n)
        parts = {"reviews": self.reviews_part, "goals": self.goals_part, "kudos": self.kudos_part,
                 "pulse": self.pulse_part}
        tabs = {"reviews": self.tab_reviews, "goals": self.tab_goals, "kudos": self.tab_kudos,
                "pulse": self.tab_pulse}
        for name in TABS:
            parts[name].visible = name == self._tab
            tabs[name].classes["on"] = name == self._tab
            state.set_attr(tabs[name], "aria-current", "page" if name == self._tab else None)
        self.my_goals_panel.add_event_handler("x-edit-goal", self._edit_goal)
        self.team_goals_panel.add_event_handler("x-edit-goal", self._edit_goal)
        self.surveys_panel.add_event_handler("x-changed", self._changed)
        self._load()

    def _load(self):
        d = state.call("performance_overview")
        if d is None:
            return
        self._d = d
        self._draw_reviews()
        self._draw_goals()
        self._draw_kudos()
        self._draw_pulse()

    def _changed(self, **event_args):
        self._load()

    # ---------------------------------------------------------------- reviews
    def _draw_reviews(self):
        d = self._d
        write = []
        for r in d["to_write"]:
            kind = "Self-review" if r["kind"] == "self" else "Manager review"
            write.append({"href": router.href("review", r["id"]), "name": r["label"],
                          "sub": "%s · due %s" % (r["cycle"], state.fmt_date(r["due"])) if r.get("due") else r["cycle"],
                          "initials": r["initials"], "tone": r["tone"], "tag": kind,
                          "tag_role": "badge-warn"})
        self.write_panel.items = write
        self.no_write.visible = not write
        about = []
        for r in d["about_me"]:
            title = "Your self-review" if r["kind"] == "self" else "Review by %s" % r["reviewer"]
            about.append({"href": router.href("review", r["id"]), "name": title,
                          "sub": "%s · submitted %s" % (r["cycle"], state.fmt_date(r["submitted_at"])),
                          "initials": r["initials"], "tone": r["tone"],
                          "tag": ("Rated %d of 5" % r["rating"]) if r["rating"] and r["kind"] == "manager" else "",
                          "tag_role": "badge-brand"})
        self.about_panel.items = about
        self.no_about.visible = not about
        hr = bool(d.get("is_admin"))
        self.cycles_box.visible = hr
        self.open_cycles_box.visible = not hr
        cycles = [dict(c, link=hr) for c in d["cycles"]]
        if hr:
            self.cycles_panel.items = cycles
            self.no_cycles.visible = not cycles
        else:
            self.open_cycles_panel.items = cycles
            self.no_open_cycles.visible = not cycles

    @handle("start_cycle_button", "click")
    def start_cycle_button_click(self, **event_args):
        from ...Dialogs.StartCycle import StartCycle
        r = alert(StartCycle(questions=self._d.get("default_questions") or []), buttons=[], role="app-dialog",
                  large=True)
        if r:
            state.toast("Review cycle started: %s to write" % state.plural(r.get("reviews", 0), "review"), "ok")
            if r.get("cycle"):
                router.go("cycle", r["cycle"]["id"])
            else:
                self._load()

    # ---------------------------------------------------------------- goals
    def _draw_goals(self):
        d = self._d
        mine = [dict(g, can_edit=True) for g in d["my_goals"]]
        self.my_goals_panel.items = mine
        self.no_goals.visible = not mine
        manager = bool(d.get("is_manager"))
        self.team_goals_box.visible = manager
        team = [dict(g, can_edit=True, show_person=True) for g in d["team_goals"]]
        self.team_goals_panel.items = team
        self.no_team_goals.visible = manager and not team
        self.add_goal_button.visible = bool(d.get("me_id"))

    def _edit_goal(self, goal=None, **event_args):
        from ...Dialogs.GoalEdit import GoalEdit
        r = alert(GoalEdit(goal=goal), buttons=[], role="app-dialog", large=True)
        if r == "deleted":
            state.toast("Goal deleted", "ok")
            self._load()
        elif r:
            state.toast("Goal saved", "ok")
            self._load()

    @handle("add_goal_button", "click")
    def add_goal_button_click(self, **event_args):
        self._edit_goal(None)

    # ---------------------------------------------------------------- kudos
    def _draw_kudos(self):
        k = self._d["kudos"]
        self.kudos_panel.items = k
        self.no_kudos.visible = not k
        self.give_kudos_button.visible = bool(self._d.get("me_id")) and bool(self._d["people"])

    @handle("give_kudos_button", "click")
    def give_kudos_button_click(self, **event_args):
        from ...Dialogs.GiveKudos import GiveKudos
        r = alert(GiveKudos(people=self._d["people"], values=self._d["values"]), buttons=[], role="app-dialog",
                  large=True)
        if r:
            state.toast("Kudos sent to %s" % r.get("to", "your colleague"), "ok")
            self._load()

    # ---------------------------------------------------------------- pulse
    def _draw_pulse(self):
        d = self._d
        s = d.get("survey")
        self.answer_box.visible = bool(s)
        self.thanks_box.visible = False
        if s:
            self.question.text = s["question"]
            self._pick(-1)
        hr = bool(d.get("is_admin"))
        self.no_survey.visible = not s and not hr
        self.results_box.visible = hr
        if hr:
            items = [dict(x, can_close=x["status"] == "open") for x in d["surveys"]]
            self.surveys_panel.items = items
            self.no_surveys.visible = not items

    def _score_handler(self, n):
        def handler(**event_args):
            self._pick(n)
        return handler

    def _pick(self, n):
        self._score[0] = n
        for i, b in enumerate(self._scale):
            b.role = ["seg", "on"] if i == n else ["seg"]
            state.set_control_attr(b, "aria-pressed", "true" if i == n else "false")

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        s = self._d.get("survey")
        if not s:
            return
        if self._score[0] < 0:
            state.toast("Choose a score from 0 to 10 first.", "error")
            state.focus(self.s5)
            return
        busy(self.send_button, True)
        try:
            r = state.call("answer_survey", s["id"], self._score[0], self.comment_box.text or "")
        finally:
            busy(self.send_button, False)
        if r is None:
            return
        self.answer_box.visible = False
        self.thanks_box.visible = True
        state.toast("Thanks, your answer is in", "ok")
        if self._d.get("is_admin"):
            self._load()
            self.answer_box.visible = False
            self.thanks_box.visible = True

    @handle("start_pulse_button", "click")
    def start_pulse_button_click(self, **event_args):
        if not confirm("Everyone gets one question: how likely they are to recommend working here, from 0 to 10. "
                       "Any open pulse closes. Answers are anonymous and results show after 3 answers.",
                       title="Start a new pulse survey?", buttons=[("Cancel", False), ("Start the pulse", True)],
                       role="app-dialog"):
            return
        busy(self.start_pulse_button, True)
        try:
            r = state.call("start_survey", "")
        finally:
            busy(self.start_pulse_button, False)
        if r is not None:
            state.toast("Pulse survey started", "ok")
            self._load()
