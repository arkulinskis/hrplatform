import anvil.server
from anvil import *

from ._anvil_designer import SetupTemplate
from ... import router, state

CURRENCIES = ["CAD", "USD", "EUR", "GBP", "AUD"]


class Setup(SetupTemplate):
    """#setup: create a company workspace (optionally with sample data) or paste an invite code.
    #join/<code>: the invite link a colleague opened."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._code = args[1] if len(args) > 1 and args[0] == "join" else ""
        joining = bool(args) and args[0] == "join"
        self.create_part.visible = not joining
        self.join_part.visible = joining
        self.currency_box.items = CURRENCIES
        self.currency_box.selected_value = "CAD"
        if joining and not self._code:
            self.join_msg.text, self.join_msg.visible = "This invite link is missing its code. Ask HR for a new one.", True

    def _done(self, company):
        state.refresh_me()
        router.go("home")

    @handle("create_button", "click")
    def create_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        if len(name) < 2:
            self.create_msg.text, self.create_msg.visible = "Give your company a name.", True
            return
        self.create_button.enabled = False
        self.create_button.text = "Setting up..."
        try:
            r = anvil.server.call("create_company", name, self.country_box.text or "", self.currency_box.selected_value,
                                  self.title_box.text or "", bool(self.sample_box.checked))
        finally:
            self.create_button.enabled = True
            self.create_button.text = "Create my workspace"
        if not r.get("ok"):
            self.create_msg.text, self.create_msg.visible = r.get("error") or "That didn't work.", True
            return
        state.toast("Welcome to %s's workspace!" % name, "ok")
        self._done(r["company"])

    def _join(self, code, msg):
        code = (code or "").strip()
        if "#join/" in code:
            code = code.split("#join/")[-1]
        if not code:
            msg.text, msg.visible = "Paste the invite code first.", True
            return
        r = anvil.server.call("join_company", code)
        if not r.get("ok"):
            msg.text, msg.visible = r.get("error") or "That invite doesn't work.", True
            return
        state.toast("You're in. Welcome to %s!" % r["company"]["name"], "ok")
        self._done(r["company"])

    @handle("join_button", "click")
    def join_button_click(self, **event_args):
        self._join(self.code_box.text, self.create_msg)

    @handle("join_now_button", "click")
    def join_now_button_click(self, **event_args):
        self._join(self._code, self.join_msg)
