from anvil import *

from ._anvil_designer import KudosCardTemplate
from ... import router, state


class KudosCard(KudosCardTemplate):
    """Kudos from one colleague to another: {from, to, to_initials, to_tone, value, message, created}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.who.text = "%s to %s" % (it["from"], it["to"])
        self.meta.text = state.ago(it["created"])
