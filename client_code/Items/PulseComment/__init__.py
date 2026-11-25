from anvil import *

from ._anvil_designer import PulseCommentTemplate


class PulseComment(PulseCommentTemplate):
    """One anonymous pulse comment: {text}."""

    def __init__(self, **properties):
        super().__init__(**properties)
