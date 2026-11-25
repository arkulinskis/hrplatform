from anvil import *

from ._anvil_designer import PolicyRowTemplate
from ... import router, state


def read_time(words):
    return "about %d min read" % max(1, int(round((words or 0) / 220.0)))


class PolicyRow(PolicyRowTemplate):
    """A policy in the handbook list: {id, title, words, require_ack, acked, ack_count?, people?}. Links to #policy/<id>."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        state.set_attr(self.link, "href", router.href("policy", it["id"]))
        bits = [read_time(it.get("words"))]
        if it.get("people") is not None and it.get("require_ack"):
            bits.append("%d of %d acknowledged" % (it.get("ack_count") or 0, it["people"]))
        self.meta.text = " · ".join(bits)
        if not it.get("require_ack"):
            self.badge.text, self.badge.role = "For reference", ["badge"]
        elif it.get("acked"):
            self.badge.text, self.badge.role = "Acknowledged", ["badge", "badge-good"]
        else:
            self.badge.text, self.badge.role = "Needs your acknowledgement", ["badge", "badge-warn"]
