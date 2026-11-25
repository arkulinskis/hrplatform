from anvil import *

from ._anvil_designer import AvatarTemplate


class Avatar(AvatarTemplate):
    """Initials in a tone circle. Decorative (the name is always written next to it)."""

    def __init__(self, **properties):
        self._initials, self._tone, self._size, self._ready = "?", 0, "md", False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        if not self._ready:
            return
        box = self.dom_nodes["box"]
        box.textContent = self._initials or "?"
        box.className = "hr-av tone-%d %s" % (int(self._tone or 0) % 6, self._size or "md")

    @property
    def initials(self):
        return self._initials

    @initials.setter
    def initials(self, value):
        self._initials = value or "?"
        self._draw()

    @property
    def tone(self):
        return self._tone

    @tone.setter
    def tone(self, value):
        self._tone = value or 0
        self._draw()

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value or "md"
        self._draw()
