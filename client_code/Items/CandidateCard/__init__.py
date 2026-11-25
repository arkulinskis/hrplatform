from anvil import *

from ._anvil_designer import CandidateCardTemplate
from ... import state

LABELS = {"applied": "Applied", "screen": "Phone screen", "interview": "Interview", "offer": "Offer",
          "hired": "Hired", "rejected": "Not moving on"}
FLOW = ["applied", "screen", "interview", "offer"]


def steps(stage):
    """(back, next) stages for the card's move buttons; None where there is no step (Hire is its own action)."""
    if stage == "rejected":
        return "applied", None
    if stage not in FLOW:
        return None, None
    i = FLOW.index(stage)
    return (FLOW[i - 1] if i > 0 else None), (FLOW[i + 1] if i + 1 < len(FLOW) else None)


class CandidateCard(CandidateCardTemplate):
    """A candidate on the pipeline board: {id, name, initials, tone, rating, source, created, notes_count, stage,
    employee_id}. Raises x-open(cand) and x-move(cand, stage, key) on its panel (StageColumn passes them on)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.source.text = it.get("source") or "Added by hand"
        r = it.get("rating") or 0
        self.rating.text = "%d/5" % r
        self.rating_box.visible = r > 0
        state.set_attr(self.rating_box, "title", "Rated %d out of 5" % r)
        n = it.get("notes_count") or 0
        self.notes.text = str(n)
        self.notes_box.visible = n > 0
        state.set_attr(self.notes_box, "title", state.plural(n, "note"))
        self.since.text = "Applied " + (state.ago(it.get("created")) or "recently")
        state.set_attr(self.open_btn, "aria-label", "Open %s" % it["name"])
        back, nxt = steps(it.get("stage"))
        self._back, self._next = back, nxt
        first = it["name"].split(" ")[0]
        if back:
            self.prev_button.text = "Reconsider" if it.get("stage") == "rejected" else "Back"
            tip = "%s: move %s to %s" % (self.prev_button.text, first, LABELS[back])
            self.prev_button.tooltip = tip
            state.set_control_attr(self.prev_button, "aria-label", tip)
            state.set_control_attr(self.prev_button, "data-key", "%s-back" % it["id"])
        else:
            self.prev_button.visible = False
        if nxt:
            tip = "Next: move %s to %s" % (first, LABELS[nxt])
            self.next_button.tooltip = tip
            state.set_control_attr(self.next_button, "aria-label", tip)
            state.set_control_attr(self.next_button, "data-key", "%s-next" % it["id"])
        else:
            self.next_button.visible = False
        self.move_box.visible = bool(back or nxt)
        self.hired.visible = it.get("stage") == "hired"

    def open_click(self, event):
        self.parent.raise_event("x-open", cand=self.item)

    @handle("prev_button", "click")
    def prev_button_click(self, **event_args):
        if self._back:
            self.parent.raise_event("x-move", cand=self.item, stage=self._back, key="%s-back" % self.item["id"])

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        if self._next:
            self.parent.raise_event("x-move", cand=self.item, stage=self._next, key="%s-next" % self.item["id"])
