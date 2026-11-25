from anvil import *

from ._anvil_designer import PeopleTemplate
from ... import router, state


class People(PeopleTemplate):
    """#people: the directory. Loads everyone once, filters in the browser as you type."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._all: list = []
        state.set_control_attr(self.search_box, "type", "search")
        state.set_control_attr(self.search_box, "aria-label", "Search people")
        self._load(False)

    def _load(self, former):
        d = state.call("list_people", former)
        self._all = d["people"]
        self.dept_box.items = [("All teams", "")] + [(x, x) for x in d["departments"]]
        self.loc_box.items = [("All locations", "")] + [(x, x) for x in d["locations"]]
        state.set_control_attr(self.dept_box, "aria-label", "Team")
        state.set_control_attr(self.loc_box, "aria-label", "Location")
        self.add_button.visible = d["can_add"]
        self.former_box.visible = d["can_add"] and d["former"] > 0
        self.count.text = state.plural(len([p for p in self._all if p["status"] != "terminated"]), "person", "people")
        self._filter()

    def _filter(self):
        q = (self.search_box.text or "").strip().lower()
        dept, loc = self.dept_box.selected_value or "", self.loc_box.selected_value or ""
        rows = []
        for p in self._all:
            if dept and p["department"] != dept:
                continue
            if loc and p["location"] != loc:
                continue
            if q and q not in (" ".join([p["name"], p["title"], p["department"], p["location"]])).lower():
                continue
            rows.append(p)
        self.people_panel.items = rows
        self.empty.visible = not rows
        self.shown.text = "" if len(rows) == len(self._all) else "Showing %d of %d" % (len(rows), len(self._all))

    @handle("search_box", "change")
    def search_box_change(self, **event_args):
        self._filter()

    @handle("dept_box", "change")
    def dept_box_change(self, **event_args):
        self._filter()

    @handle("loc_box", "change")
    def loc_box_change(self, **event_args):
        self._filter()

    @handle("former_box", "change")
    def former_box_change(self, **event_args):
        self._load(bool(self.former_box.checked))

    @handle("add_button", "click")
    def add_button_click(self, **event_args):
        from ...Dialogs.AddPerson import AddPerson
        person = alert(AddPerson(), buttons=[], role="app-dialog", large=True)
        if person:
            state.toast("%s added. Their onboarding checklist is ready." % person["name"], "ok")
            router.go("person", person["id"])
