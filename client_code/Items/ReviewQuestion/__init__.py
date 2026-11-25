from anvil import *

from ._anvil_designer import ReviewQuestionTemplate
from ... import state


class ReviewQuestion(ReviewQuestionTemplate):
    """One review question with its answer: {key, n, question, answer, editable}. The page reads answers back
    with value() (key, text)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.question.text = "%d. %s" % (it["n"], it["question"])
        state.heading(self.question, 3)
        editable = bool(it.get("editable"))
        self.field.visible = editable
        self.answer_text.visible = not editable
        if editable:
            self.answer_box.text = it.get("answer") or ""
            state.set_control_attr(self.answer_box, "aria-label", "Answer to question %d" % it["n"])
        else:
            self.answer_text.text = it.get("answer") or "No answer."
            if not it.get("answer"):
                self.answer_text.role = ["pfx-answer", "pfx-answer-none"]

    def value(self):
        return self.item["key"], (self.answer_box.text or "") if self.item.get("editable") else (self.item.get("answer") or "")
