from anvil import *

from ._anvil_designer import OrgTemplate
from ... import router, state


class Org(OrgTemplate):
    """#org (or #org/<id> to highlight someone): the whole company as a tidy tree, open roles dashed."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        d = state.call("org_chart")
        people = sorted(d["nodes"], key=lambda n: n["name"].lower())
        self.sub.text = "%s · %s%s" % (d["company"], state.plural(len(people), "person", "people"),
                                      (" · %s" % state.plural(len(d["open_roles"]), "open role")) if d["open_roles"] else "")
        self.find_box.items = [("Find someone...", "")] + [(n["name"], n["id"]) for n in people]
        state.set_control_attr(self.find_box, "aria-label", "Find someone on the chart")
        focus = args[0] if args else (state.emp_id() or "")
        self.chart.focus = focus
        self.chart.data = d

    @handle("find_box", "change")
    def find_box_change(self, **event_args):
        if self.find_box.selected_value:
            self.chart.focus = self.find_box.selected_value

    @handle("chart", "select")
    def chart_select(self, emp_id, **event_args):
        router.go("person", emp_id)
