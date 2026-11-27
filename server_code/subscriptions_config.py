"""What the paid plan means in THIS app (Subscriptions.py is the same in every app; this file is the app's own).

    APP_NAME, PLAN_NAME   shown on the offer and on Stripe
    PRICE                 monthly price in USD (per seat when PER_SEAT)
    YEARLY                yearly price in USD, or None for monthly only
    TRIAL_DAYS            free trial before the first charge (your review window)
    PER_SEAT              True: the plan is bought per seat (employees, team members)
    FREE_SEATS            seats anyone may use without a plan (Subscriptions.seats_ok)
    MIN_SEATS             smallest seat count on a paid plan
    FREE / PAID           what everyone gets / what the plan adds (short lines for the offer)
    owner_of(user)        optional: who pays for this person (e.g. the workspace or studio owner); default themselves
Written by tools/payments_rollout.py from APP_MAKER/money/lifetime/plan.json; edit freely afterwards.
"""
APP_NAME = "HR Platform"
PLAN_NAME = "Pro"
PRICE = 4
YEARLY = 40
TRIAL_DAYS = 14
PER_SEAT = True
FREE_SEATS = 5
MIN_SEATS = 8
FREE = [
    "Up to 5 employees, with every HR feature",
    "Your full company data export, any day",
]
PAID = [
    "Employee 6 and up ($4 per employee a month, 8 seats minimum)",
    "Reports: headcount, turnover, hiring, time off",
    "People list and payroll exports",
]
# Plan (money/lifetime/plan.json): Per employee per month, $4 per employee/mo, minimum $29/mo (MIN_SEATS 8 = $32).


def owner_of(user):
    """The company's owner (who made the workspace) pays for everyone in it."""
    if user is None:
        return None
    company = user["company"]
    if company is not None and company["owner"] is not None:
        return company["owner"]
    return user
