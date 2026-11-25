import datetime

from anvil import *

from ._anvil_designer import HomeTemplate
from ... import state


class Home(HomeTemplate):
    """#home: the dashboard. One server call (get_home): the "Needs you" inbox, who's out, birthdays and work
    anniversaries, new faces, announcements, kudos, my balances and (HR) the key numbers."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        state.heading(self.hello, 1)
        d = state.call("get_home")
        me = d["me"] or {}
        hour = datetime.datetime.now().hour
        part = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        self.hello.text = "%s, %s" % (part, me.get("first") or "there")
        today = d["today"]
        wd = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
            datetime.date(int(today[:4]), int(today[5:7]), int(today[8:10])).weekday()]
        self.today.text = "%s %s · %s" % (wd, state.fmt_date(today), d["company"])
        st = d.get("stats")
        self.stats_part.visible = bool(st)
        if st:
            self.s_head.text, self.s_start.text = str(st["headcount"]), str(st["starting"])
            self.s_jobs.text, self.s_cands.text, self.s_pending.text = str(st["open_jobs"]), str(st["candidates"]), str(st["pending"])
        self.needs_panel.items = d["needs"]
        self.needs_count.text = str(len(d["needs"]))
        self.needs_count.visible = bool(d["needs"])
        self.no_needs.visible = not d["needs"]
        anns = d["announcements"]
        for a in anns:
            a["can_delete"] = False
        self.ann_panel.items = anns
        self.no_ann.visible = not anns
        self.kudos_panel.items = d["kudos"][:3]
        self.no_kudos.visible = not d["kudos"]
        out = []
        for o in d["out_week"]:
            now = o["start"] <= today <= o["end"]
            out.append({"id": o["person_id"], "name": o["person"], "initials": o["initials"], "tone": o["tone"],
                        "sub": "%s · %s" % (o["type"], state.date_range(o["start"], o["end"])),
                        "tag": "Out today" if now and o["status"] == "approved" else ("Waiting" if o["status"] == "pending" else ""),
                        "tag_role": "badge-warn" if o["status"] == "pending" else "badge-brand"})
        self.out_panel.items = out
        self.no_out.visible = not out
        self.events_panel.items = d["celebrations"]
        self.no_events.visible = not d["celebrations"]
        joiners = [{"id": j["id"], "name": j["name"], "initials": j["initials"], "tone": j["tone"],
                    "sub": "%s · %s %s" % (j["title"] or j["department"], "starts" if j["start_date"] > today else "joined",
                                           state.fmt_date(j["start_date"], False))} for j in d["joiners"]]
        self.joiners_panel.items = joiners
        self.joiners_part.visible = bool(joiners)
        self.bal_panel.items = d["balances"]
        self.bal_part.visible = bool(d["balances"])
