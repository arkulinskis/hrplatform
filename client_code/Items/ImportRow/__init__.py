from anvil import *

from ._anvil_designer import ImportRowTemplate


class ImportRow(ImportRowTemplate):
    """One previewed CSV row from Staff.import_people: {line, name, email, title, department, issues}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.line.text = "Row %s" % it.get("line")
        self.name.text = it.get("name") or "(no name)"
        self.sub.text = " · ".join(x for x in (it.get("email"), it.get("title"), it.get("department")) if x)
        if it.get("issues"):
            self.issues.text, self.issues.role = it["issues"], ["badge", "badge-bad"]
            self.row.classes["bad"] = True
        else:
            self.issues.text, self.issues.role = "Ready", ["badge", "badge-good"]
