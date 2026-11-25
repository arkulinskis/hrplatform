import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import ApplyTemplate
from ... import state


class Apply(ApplyTemplate):
    """The public application form for one job (careers page). A hidden "website" field and the time spent on the
    form keep bots out (the server pretends it worked for them). Closes with True once sent."""

    def __init__(self, job=None, company="", **properties):
        super().__init__(**properties)
        self._job = job or {}
        self._t0 = window.Date.now()
        self._sent = False
        self.job_line.text = "%s%s" % (self._job.get("title", ""), (" at " + company) if company else "")
        self.done_part.visible = False
        for box, auto in ((self.name_box, "name"), (self.email_box, "email"), (self.phone_box, "tel"),
                          (self.link_box, "url")):
            state.set_control_attr(box, "autocomplete", auto)
        state.set_control_attr(self.website, "tabindex", "-1")
        state.set_control_attr(self.website, "autocomplete", "off")
        state.set_control_attr(self.website, "aria-label", "Leave this empty")
        state.set_control_attr(self.website, "name", "website")
        state.live(self.done_text)

    @handle("", "show")
    def form_show(self, **event_args):
        self.name_box.focus()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=True)

    def _fail(self, text, box=None):
        self.message.text, self.message.visible = text, True
        if box is not None:
            box.focus()

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        email = (self.email_box.text or "").strip()
        if len(name) < 2:
            return self._fail("Add your name.", self.name_box)
        if "@" not in email or "." not in email.split("@")[-1]:
            return self._fail("Add an email address we can reach you at.", self.email_box)
        self.message.visible = False
        data = {"name": name, "email": email, "phone": self.phone_box.text or "", "link": self.link_box.text or "",
                "cover": self.cover_box.text or "", "website": self.website.text or "",
                "ms": int(window.Date.now() - self._t0)}
        self.send_button.enabled, self.send_button.text = False, "Sending..."
        try:
            r = anvil.server.call("apply_to_job", self._job.get("id"), data)
        finally:
            self.send_button.enabled, self.send_button.text = True, "Send application"
        if not r.get("ok"):
            return self._fail(r.get("error") or "That didn't send. Please try again.")
        self._sent = True
        self.form_part.visible = False
        self.done_part.visible = True
        state.focus(self.close_button)
