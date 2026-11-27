"""The paid plan, HR Platform's way (kit: subscription.py + server Subscriptions.py, same in every app).

The company owner pays for everyone in the company (subscriptions_config.owner_of), so only the owner sees the
plan offer; HR admins who aren't the owner get a note to ask them. Everything here is a no-op while the gate is off.

    plan.need(feature)   show the offer (owner) or the "ask your owner" note
    plan.gate(feature)   True if the plan is on (or the gate is off); otherwise plan.need(...) and False
"""
from . import state, subscription

ASK_OWNER = "That's on the paid plan. Ask your company's owner to start it (Profile, Plan and billing)."


def need(feature=None):
    if (state.me() or {}).get("is_owner"):
        subscription.offer(feature)
    else:
        state.toast(ASK_OWNER, "error")


def gate(feature=None):
    if subscription.active():
        return True
    need(feature)
    return False
