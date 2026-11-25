from anvil import *

from ._anvil_designer import SurveyCardTemplate
from ... import router, state


class SurveyCard(SurveyCardTemplate):
    """A pulse survey's results for HR: {id, question, status, created, answers, invited, visible, min, enps?,
    promoters?, passives?, detractors?, comments?, can_close?}. Close raises x-changed on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        is_open = it["status"] == "open"
        self.status.text = "Open" if is_open else "Closed"
        self.status.role = ["badge", "badge-good"] if is_open else ["badge"]
        self.close_button.visible = bool(it.get("can_close"))
        self.meta.text = "Started %s · %d of %d answered" % (state.fmt_date(it["created"]), it["answers"],
                                                             it.get("invited") or 0)
        shown = bool(it.get("visible"))
        self.shown_box.visible = shown
        self.hidden_box.visible = not shown
        if not shown:
            self.waiting.text = ("Waiting for %d answers (%d so far). Results stay hidden until then, so nobody "
                                 "can be singled out." % (it.get("min") or 3, it["answers"]))
            return
        score = it.get("enps") or 0
        self.score.text = ("+%d" % score) if score > 0 else str(score)
        pro, pas, det = it.get("promoters") or 0, it.get("passives") or 0, it.get("detractors") or 0
        total = max(1, pro + pas + det)
        for bar, n in ((self.pro_bar, pro), (self.pas_bar, pas), (self.det_bar, det)):
            bar.style["width"] = "%.1f%%" % (100.0 * n / total)
        self.pro_text.text = "%d promoters (9-10)" % pro
        self.pas_text.text = "%d passives (7-8)" % pas
        self.det_text.text = "%d detractors (0-6)" % det
        state.set_attr(self.split_bar, "aria-label", "%d promoters, %d passives, %d detractors" % (pro, pas, det))
        comments = [{"text": c} for c in (it.get("comments") or [])]
        self.comments_panel.items = comments
        self.no_comments.visible = not comments

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        if confirm("People can't answer it any more. The results stay.", title="Close this pulse survey?",
                   buttons=[("Cancel", False), ("Close the survey", True)], role="app-dialog"):
            if state.call("close_survey", self.item["id"]) is not None:
                state.toast("Pulse survey closed", "ok")
                self.parent.raise_event("x-changed")
