# HR Platform

An HR workspace for small and mid-size companies, in the spirit of BambooHR: one record per person, used by every
part of the app. HR keeps employee records, time off, hiring, onboarding, reviews, policies and reports in one calm
place; managers approve and review their team; employees serve themselves from any phone. Built on
[Anvil](https://anvil.works) as native Anvil Forms (Python + HTML templates, a layout, custom components, RepeatingPanels).

- **App repo:** github.com/arkulinskis/hrplatform (branch `master`). Anvil pulls `master`.
- **Live:** https://hr-platform.anvil.app (Anvil app id KDAE63RLZGA32RE2).
- **Backlog:** [BACKLOG.md](BACKLOG.md): every researched feature by category, what's built and what's next.

## What it does

**Workspaces and roles.** Each company is a private workspace. Whoever creates it is its first **HR admin**; others
join with a one-time invite link from their profile. Roles: HR admin (everything), manager (anyone with people below
them in the reporting line) and employee. A new workspace can start with a fictional **sample company** (26 people,
open roles, a review cycle, requests to approve), removable in one click in Settings. HR can **preview the app as any
colleague** ("view as") to check what they see; a yellow bar shows it.

**People.** Directory with search and team/location filters; profiles with About, Job and pay, Time off, Goals,
Documents (files up to 8 MB, equipment) and History tabs. Field-level privacy enforced on the server: colleagues see
name, job, team, work email, pronouns, manager and birthday (day and month); pay goes only to the person, the managers
above them and HR; personal details, files and history to the person and HR; HR notes to HR only. Job and pay changes
take an **effective date** and land in the change history. Add a person (with an onboarding checklist), import many
from a pasted spreadsheet (headers matched by name, preview, managers linked by email), mark on leave / back, offboard
(last day, reason, regretted, rehire; reports move up to the manager). **Org chart** drawn from reporting lines, open
roles dashed, find someone, click to open.

**Home.** "Needs you": one inbox for time off approvals, reviews to write, onboarding tasks, policies to acknowledge
and the pulse survey. Who's out this week, birthdays and work anniversaries, new faces, announcements, kudos, your
balances, and (HR) a strip of key numbers.

**Time off.** Leave types with yearly allowances (0 = no limit), paid/unpaid; requests counted in working days
(weekends and company holidays skipped), overlap and balance checks; approvals by anyone above the person or HR; HR can
enter leave for someone; balances; a who's-out month calendar (the leave type is hidden from colleagues); public
holidays (Canada/Québec defaults).

**Hiring.** Jobs with team, location, salary range and hiring manager; a public **careers page** (`#careers/<slug>`,
demo: `#careers/larkspur`) with an application form (honeypot, time-on-page and rate limits); a pipeline board
(Applied, Phone screen, Interview, Offer, Hired, Not moving on), ratings, notes; **Hire** creates the employee and their
onboarding checklist. Hiring managers see their own jobs; everyone sees open roles.

**Onboarding and offboarding.** Checklists from the company's templates; each task owned by HR, IT, the manager or the
new hire, with due dates counted from the start date or last day; "Your tasks"; HR adds and removes tasks.

**Performance.** Review cycles (self + manager review for everyone, editable questions, 1-5 ratings, drafts, submit;
the person sees the manager review after the cycle closes), cycle progress and rating distribution for HR; goals with
progress and status (managers see their team's); kudos tied to company values; an anonymous **eNPS pulse** (answers
stored without names, shown after 3 answers).

**Policies and news.** Policies people acknowledge (who and when; editing asks everyone again), announcements (pinned
first).

**Reports (HR).** Headcount, starting soon, on leave, 12-month turnover, new hires, regretted leavers; charts for the
headcount trend, hires and leavers, team, location, type, tenure, time off by type, the hiring funnel and eNPS; CSV of
people (optionally with pay); a **payroll export** for any period (pay, changes, paid and unpaid days off).

**Settings (HR).** Company name, country, currency; teams, locations and values; leave types and holidays; onboarding
and offboarding templates; spreadsheet import; full company export (JSON); remove sample data; the company audit log.

**Site admin** (the app owner, not company HR): users, old feedback, the public demo company. Feedback goes through
Prepsto ("Submit feedback" in the footer).

## Paid plan ($4 per employee a month, first 5 employees free)

Off until the App Secret `stripe_secret_key` holds a Stripe key: until then everything stays free and no prices show.
Setup: `APP_MAKER/money/lifetime/STRIPE_SETUP.md` (webhook optional: `/_/api/subscription/stripe`, secret `stripe_webhook_secret`).

- **Free:** up to 5 employees with every HR feature; the full company data export.
- **Paid (14-day trial, per seat, 8 seats minimum):** employee 6 and up (`Staff.add_person`, `import_people`, rehiring in
  `set_status`, all through `Workspace.seats_ok`), Reports and the people / payroll CSV exports (`Reports.py`, `Workspace.paid`).
  Existing people are never touched: only adding more is checked. The company owner pays for everyone
  (`subscriptions_config.owner_of`); other HR admins are told to ask them (`client_code/plan.py`).
- Kit: `server_code/Subscriptions.py` + `subscriptions_config.py`, `client_code/subscription.py`, `Dialogs/PlanOffer`,
  `Dialogs/PlanAdmin` (Admin, "Paid plans"); "Plan and billing" on Profile once the gate is on.

## Setting it up in Anvil (once)

1. Anvil editor: **Create app → Clone from GitHub**, paste `https://github.com/arkulinskis/hrplatform`.
2. Check the **Users** service (email + password, Continue with Google, sign-up on).
3. Accept the **Schema Mismatch** alert with **"The schema of the source code is correct"** (creates the 26 tables).
4. **App Secrets**: create `admin_emails` = your email (never written in the code). Run it, sign in with **Continue with
   Google** using that email (it becomes the site admin), then **Publish**.
5. Admin status report (users, rows, errors): `/_/api/admin/status` while signed in as an admin.

<!-- libraries:start -->
## Libraries and outside services

What this project uses besides its own code. Generated by `APP_MAKER/tools/libraries.py`; to change it, edit `APP_MAKER/libraries/catalog.py` and re-run the script.

| Name | How it gets in | Used here for |
|---|---|---|
| [Google Fonts](https://fonts.google.com) | Loaded from a CDN | Bricolage Grotesque, Source Sans 3 |

**Built into the browser:** localStorage, Clipboard, File downloads (Blob).

**Anvil platform:** Anvil, Anvil Data Tables, Anvil JS bridge (anvil.js), Anvil Secrets, Anvil Users, Anvil Google service, Anvil Media.

**Build and test tools (not shipped):** axe-core, Node.js, Headless Chrome (DevTools Protocol), PyYAML.

<!-- libraries:end -->

## Working on it

See `.claude/skills/hrplatform/SKILL.md` and `APP_MAP.md`. In short:

```
python tools/check.py                    # Anvil's validator, JS syntax, asset hashes, server tests -> ALL CHECKS PASSED
python -I tools/ui_test.py               # the real app in the Anvil App Server (Docker) driven by headless Chrome
python -I tools/ui_test.py --shots DIR   # + screenshots of every page (desktop/phone, light/dark, guest/member)
git push origin master                   # deploy
```

## Project layout

```
client_code/    startup.py, router.py (pages + who may open them), state.py (helpers), auth.py, legal.py
  Layouts/Shell header, menus (NAV desktop, TABS phone), view-as bar, footer
  Pages/        Landing Auth Setup Home People Person Org TimeOff Hiring Job Careers Onboarding Checklist
                Performance Review Cycle Docs Policy Reports Settings More Profile Admin
  Components/   Avatar, OrgChart, Chart, MonthCalendar (the last three wrap theme/assets/hr-engines.js)
  Items/        list rows (PersonCard, NeedRow, BalanceCard, GoalRow, LeaveRow, CandidateCard ...)
  Dialogs/      EditPerson, AddPerson, Terminate, Invite, RequestTimeOff, Candidate, JobEdit, GoalEdit ...
server_code/    Workspace (context, roles, permissions, settings, export) · Staff (people) · Leave · Hiring · Onboard
                Perform (reviews, goals, kudos, pulse) · Docs (policies, news) · Dashboard (home) · Reports
                Sample (sample company) · DemoData (public demo company) · common, Accounts, Admin, AppStatus ...
theme/assets/   app.css (tokens), hr.css (shared), hr-time.css, hr-hiring.css, hr-perf.css, hr-engines.js, icons
tools/          check.py, ui_test.py + ui/ (flow.js + flow_<area>.js, hrseed.js, phone, a11y, design), testing/
```
