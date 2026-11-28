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


# The app's video on the Addanapp YouTube channel (APP_MAKER/youtube/manifest.json), shown in the Watch section.
YT_VIDEO = "C9M-e-trEo0"


class Landing(LandingTemplate):
    """#landing, the front page for visitors (Persuade mode): a live org chart that draws itself, how it works,
    features, the complaints we fixed, audiences, FAQ. Static copy lives in the template."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.dom_nodes["yt_cover"].addEventListener("click", self._play)
        me = state.me()
        self.guest_cta.visible = not me
        self.member_cta.visible = bool(me)
        if me:
            state.set_attr(self.band_link, "href", "#home")
        self.chart.data = SAMPLE

    def _play(self, event):
        """Swap the video's cover for YouTube's player (privacy-enhanced); nothing loads from YouTube before this click."""
        self.dom_nodes["yt_frame"].innerHTML = (
            '<iframe src="https://www.youtube-nocookie.com/embed/' + YT_VIDEO + '?autoplay=1&rel=0&playsinline=1" '
            'title="HR Platform video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe>')
