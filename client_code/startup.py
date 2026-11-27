"""The app starts here (anvil.yaml: startup module). One server call to learn who is signed in (Anvil's loading
spinner shows meanwhile), the Privacy & Terms kit, then the page for the address in the browser bar."""
import anvil.server

from . import legal, router, session_guard, state

session_guard.start()  # an expired server session reloads quietly instead of "Session expired, refresh now"
LEGAL_THEME = {"accent": "#2f6b4f"}  # colours for the Privacy & Terms page (match --c-brand in app.css)

legal.setup(LEGAL_THEME)
state.set_me(anvil.server.call("get_me"))
if state.me():
    legal.refresh_soon()
from . import subscription  # payments: free until the App Secret stripe_secret_key is set
subscription.handle_return()
router.start()
