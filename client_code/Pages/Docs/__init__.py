from anvil import *

from ._anvil_designer import DocsTemplate
from ... import router, state


class Docs(DocsTemplate):
    """#docs: announcements (HR posts and deletes them) and the policy list with each one's acknowledgement state
    (HR sees how many people acknowledged and writes new policies)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.anns_panel.add_event_handler("x-changed", self._changed)
        self._load()

    def _changed(self, **event_args):
        state.toast("Announcement deleted", "ok")
        self._load()

    def _load(self):
        d = state.call("docs_overview")
        if d is None:
            return
        hr = bool(d.get("is_admin"))
        self.announce_button.visible = hr
        self.policy_button.visible = hr
        anns = [dict(a, can_delete=hr) for a in d["announcements"]]
        self.anns_panel.items = anns
        self.no_anns.visible = not anns
        if hr:
            self.no_anns_text.text = "Post news everyone should see: an office closure, a new joiner, a reminder."
            self.no_policies_text.text = "Add your handbook policies (remote work, expenses, code of conduct) and " \
                                         "ask people to acknowledge them."
        pols = d["policies"]
        self.policies_panel.items = pols
        self.no_policies.visible = not pols
        todo = [p for p in pols if p.get("require_ack") and not p.get("acked")]
        self.todo_line.visible = bool(todo)
        if todo:
            self.todo_line.text = "%s waiting for your acknowledgement." % state.plural(len(todo), "policy", "policies")

    @handle("announce_button", "click")
    def announce_button_click(self, **event_args):
        from ...Dialogs.Announce import Announce
        if alert(Announce(), buttons=[], role="app-dialog", large=True):
            state.toast("Announcement posted", "ok")
            self._load()

    @handle("policy_button", "click")
    def policy_button_click(self, **event_args):
        from ...Dialogs.PolicyEdit import PolicyEdit
        p = alert(PolicyEdit(), buttons=[], role="app-dialog", large=True)
        if p:
            state.toast("Policy saved", "ok")
            router.go("policy", p["id"])
