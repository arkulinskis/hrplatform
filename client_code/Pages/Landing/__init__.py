from anvil import *

from ._anvil_designer import LandingTemplate
from ... import state

# The hero's sample company (fictional): drawn by the same engine as the real org chart.
SAMPLE = {"company": "Larkspur Studio", "nodes": [
    {"id": "a", "name": "Amara Okafor", "title": "Chief Executive", "initials": "AO", "tone": 0, "manager_id": None},
    {"id": "b", "name": "Mateus Silva", "title": "CTO", "initials": "MS", "tone": 2, "manager_id": "a"},
    {"id": "c", "name": "Grace Kim", "title": "Head of Sales", "initials": "GK", "tone": 4, "manager_id": "a"},
    {"id": "d", "name": "Priya Raman", "title": "People Partner", "initials": "PR", "tone": 3, "manager_id": "a"},
    {"id": "e", "name": "Lena Fischer", "title": "Eng. Manager", "initials": "LF", "tone": 1, "manager_id": "b"},
    {"id": "f", "name": "Noor Haddad", "title": "Design Lead", "initials": "NH", "tone": 5, "manager_id": "b"},
    {"id": "g", "name": "Oliver Bennett", "title": "Account Exec.", "initials": "OB", "tone": 2, "manager_id": "c"},
    {"id": "h", "name": "Mei Chen", "title": "Customer Success", "initials": "MC", "tone": 0, "manager_id": "c",
     "status": "leave"},
    {"id": "i", "name": "Jonah Reyes", "title": "Backend Engineer", "initials": "JR", "tone": 4, "manager_id": "e",
     "status": "onboarding"}],
    "open_roles": [{"title": "Senior Backend Eng.", "department": "Engineering", "manager_id": "e"}]}


class Landing(LandingTemplate):
    """#landing, the front page for visitors (Persuade mode): a live org chart that draws itself, how it works,
    features, the complaints we fixed, audiences, FAQ. Static copy lives in the template."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me()
        self.guest_cta.visible = not me
        self.member_cta.visible = bool(me)
        if me:
            state.set_attr(self.band_link, "href", "#home")
        self.chart.data = SAMPLE
