import anvil.server
from anvil import *

from ._anvil_designer import ImportPeopleTemplate
from ... import plan, state

TEMPLATE_HEADERS = ["First name", "Last name", "Email", "Title", "Department", "Location", "Manager email",
                    "Start date", "Employment type", "Birthday", "Pay rate"]
TEMPLATE_EXAMPLE = ["Ana", "Silva", "ana.silva@example.com", "Product Designer", "Design", "Remote",
                    "", "2026-12-01", "Full-time", "1992-04-18", "78000"]
FIELD_NAMES = {"first_name": "First name", "last_name": "Last name", "full_name": "Name", "work_email": "Email",
               "title": "Title", "department": "Department", "location": "Location", "manager_email": "Manager email",
               "start_date": "Start date", "employment_type": "Employment type", "birthday": "Birthday",
               "pay_rate": "Pay rate"}


def download_template():
    """The CSV template with its header row and one example person."""
    text = ",".join(TEMPLATE_HEADERS) + "\n" + ",".join(TEMPLATE_EXAMPLE) + "\n"
    state.download_text(text, "people-import-template.csv", "text/csv")


class ImportPeople(ImportPeopleTemplate):
    """Paste CSV/TSV -> Preview (import_people(text, False)) -> Import N people (import_people(text, True)).
    Rows with problems are skipped. Closes with {added, skipped} or None."""

    def __init__(self, **properties):
        self._previewed = ""
        super().__init__(**properties)
        self.preview_part.visible = False

    @handle("", "show")
    def form_show(self, **event_args):
        self.csv_box.focus()

    @handle("csv_box", "change")
    def csv_box_change(self, **event_args):
        if (self.csv_box.text or "") != self._previewed:
            self.import_button.enabled = False
            self.import_button.text = "Import people"

    @handle("template_button", "click")
    def template_button_click(self, **event_args):
        download_template()

    def _error(self, text):
        self.message.text, self.message.visible = text, True

    @handle("preview_button", "click")
    def preview_button_click(self, **event_args):
        text = self.csv_box.text or ""
        if not text.strip():
            return self._error("Paste the rows first, starting with the header row.")
        self.message.visible = False
        self.preview_button.enabled = False
        try:
            r = anvil.server.call("import_people", text, False)
        finally:
            self.preview_button.enabled = True
        if not r.get("ok"):
            self.preview_part.visible = False
            return self._error(r.get("error") or "That didn't work.")
        self._previewed = text
        good = r["total"] - r["problems"]
        self.rows_panel.items = r["rows"]
        self.summary.text = "%s found · %s ready%s" % (
            state.plural(r["total"], "row"), state.plural(good, "person", "people"),
            (" · %s with problems (skipped)" % state.plural(r["problems"], "row")) if r["problems"] else "")
        self.mapped.text = "Columns used: " + ", ".join(FIELD_NAMES.get(m, m) for m in r.get("mapped") or [])
        self.preview_part.visible = True
        self.import_button.enabled = good > 0
        self.import_button.text = "Import %s" % state.plural(good, "person", "people") if good else "Nothing to import"

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("import_button", "click")
    def import_button_click(self, **event_args):
        self.import_button.enabled = False
        try:
            r = anvil.server.call("import_people", self._previewed, True)
        except Exception:
            self.import_button.enabled = True
            raise
        if not r.get("ok"):
            self.import_button.enabled = True
            if r.get("plan"):   # more than the free / paid seats: the paid plan (only once Stripe is set up)
                plan.need("Employee 6 and up")
            return self._error(r.get("error") or "That didn't work.")
        self.raise_event("x-close-alert", value={"added": r["added"], "skipped": r["skipped"]})
