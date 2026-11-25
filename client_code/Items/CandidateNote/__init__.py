from anvil import *

from ._anvil_designer import CandidateNoteTemplate
from ... import state


class CandidateNote(CandidateNoteTemplate):
    """One line of a candidate's notes timeline: {by, text, when, system?}. System notes (moves, hires) are quieter."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.row.classes["sys"] = bool(it.get("system"))
        when = state.ago(it.get("when")) if it.get("when") else ""
        self.meta.text = " · ".join([b for b in (it.get("by") or "", when) if b])
