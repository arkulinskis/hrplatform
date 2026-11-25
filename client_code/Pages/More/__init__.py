from anvil import *

from ._anvil_designer import MoreTemplate
from ... import router, state


class More(MoreTemplate):
    """#more: every area in one list (the phone's "More" tab), plus "view as" for HR admins."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me() or {}
        self.sub.text = me.get("company") or ""
        state.set_attr(self.my_link, "href", router.href("person", me.get("emp_id") or ""))
        self.reports_link.visible = state.is_hr()
        self.settings_link.visible = state.is_hr()
        can = me.get("real_role") == "admin" and not me.get("viewing_as")
        self.preview_part.visible = can
        if can:
            d = state.call("list_people", False)
            self.person_box.items = [("Choose a colleague", "")] + [
                ("%s (%s)" % (p["name"], p["title"] or p["department"]), p["id"]) for p in d["people"] if not p["is_me"]]
            state.set_control_attr(self.person_box, "aria-label", "Colleague to preview as")

    @handle("preview_button", "click")
    def preview_button_click(self, **event_args):
        if not self.person_box.selected_value:
            state.toast("Choose a colleague first.", "error")
            return
        r = state.call("view_as", self.person_box.selected_value)
        if r:
            state.refresh_me()
            state.toast("Previewing as %s." % r["viewing_as"], "ok")
            router.go("home")
