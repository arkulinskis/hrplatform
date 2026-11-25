from anvil import *

from ._anvil_designer import StageColumnTemplate

EMPTY = {"applied": "New applications land here.", "screen": "Nobody to call yet.",
         "interview": "No interviews lined up.", "offer": "No offers out.", "hired": "Nobody hired yet.",
         "rejected": "Nobody here."}


class StageColumn(StageColumnTemplate):
    """One pipeline stage: {stage, label, candidates}. Passes its cards' x-open / x-move events on to its own panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        cands = it.get("candidates") or []
        self.count.text = str(len(cands))
        self.col.classes["k-" + it["stage"]] = True
        self.cards_panel.items = cands
        self.empty.text = EMPTY.get(it["stage"], "Nobody here.")
        self.empty.visible = not cands
        self.cards_panel.add_event_handler("x-open", self._open)
        self.cards_panel.add_event_handler("x-move", self._move)

    def _open(self, cand=None, **event_args):
        self.parent.raise_event("x-open", cand=cand)

    def _move(self, cand=None, stage=None, key=None, **event_args):
        self.parent.raise_event("x-move", cand=cand, stage=stage, key=key)
