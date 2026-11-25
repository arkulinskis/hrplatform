from anvil import *

from ._anvil_designer import FileRowTemplate
from ... import router, state


class FileRow(FileRowTemplate):
    """An employee file: {id, name, size, by, created}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        kb = (it["size"] or 0) / 1024.0
        self.meta.text = "%s · added by %s %s" % ("%.1f MB" % (kb / 1024) if kb > 1024 else "%d KB" % max(1, kb),
                                                  it["by"] or "HR", state.ago(it["created"]))

    @handle("open_button", "click")
    def open_button_click(self, **event_args):
        import anvil.media
        import anvil.server
        m = anvil.server.call("get_file", self.item["id"])
        if m is not None:
            anvil.media.download(m)

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if confirm("The file is deleted for good.", title="Delete %s?" % self.item["name"],
                   buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            if state.call("delete_file", self.item["id"]) is not None:
                self.parent.raise_event("x-changed")
