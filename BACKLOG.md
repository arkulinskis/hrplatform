# HR Platform: feature backlog

From the research of 2026-11-25 (HR responsibilities, BambooHR's modules, Rippling, Gusto, HiBob, Personio, Workday,
Deel, Lattice, Workable and others, and common complaints from G2/Capterra reviews).
`[x]` built · `[~]` partly built (what's missing is noted) · `[ ]` to do. P1 = must-have, P2 = next, P3 = later.

## Core HR
- [x] P1 Employee profile: personal, contact, address, emergency contact
- [x] P1 Job info: title, team, location, manager, employment type, start date, access level
- [x] P1 Effective-dated job and pay changes, kept as a history (who, what, when it takes effect)
- [x] P1 Status lifecycle: starting soon, active, on leave, left (with rehire)
- [x] P1 Bulk import from a pasted spreadsheet (CSV/TSV, headers matched by name, preview with problems, managers by email)
- [ ] P1 Custom fields (text, number, date, dropdown) per section
- [~] P1 Profile photo and pronouns (pronouns built; initials avatars instead of photos)
- [x] P2 Private HR notes on an employee (HR admins only)
- [ ] P2 Custom tables (certifications, dependants)
- [ ] P2 Several legal entities per workspace
- [ ] P2 Bulk edit (change many people at once)
- [ ] P3 Employee ID numbering
- [ ] P3 Duplicate detection on import (only same-email detection today)

## Org and people directory
- [x] P1 Searchable directory with team and location filters (former employees for HR)
- [x] P1 Org chart drawn from reporting lines (tidy tree, find someone, click to open)
- [x] P2 Open roles shown dashed on the org chart
- [x] P2 Birthdays (day and month only) and work anniversaries on the home page
- [ ] P2 Org chart export (PNG/PDF) and print
- [ ] P2 Team pages (members, lead, description)
- [ ] P3 "Ask me about" skills on profiles
- [ ] P3 Re-org planning (drag and drop scenarios)

## Hiring (ATS)
- [x] P1 Job openings with description, team, location, salary range, hiring manager, status
- [x] P1 Public careers page with an application form (spam guards, no duplicates)
- [x] P1 Candidate pipeline board (Applied, Phone screen, Interview, Offer, Hired, Not moving on)
- [x] P1 Candidate profile with link, message, rating and notes timeline
- [x] P1 Hire in one click: creates the employee and their onboarding checklist
- [x] P2 Hiring managers see only their own jobs; everyone sees open roles to refer people
- [ ] P2 Interview scheduling with calendar integration
- [ ] P2 Interview scorecards
- [ ] P2 Email templates and emails to candidates from the app
- [ ] P2 Offer letters from templates with e-signature
- [ ] P2 Job board posting (Indeed, LinkedIn, Google for Jobs schema)
- [ ] P2 Requisition approval
- [ ] P3 Referral programme, talent pool, recruiting analytics beyond the funnel

## Onboarding
- [x] P1 Checklists from company templates (editable in Settings)
- [x] P1 Tasks owned by HR, IT, the manager or the new hire, with due dates counted from the start date
- [x] P1 "Your tasks" list and the tasks in the home inbox
- [~] P1 Pre-boarding: the new hire can fill in their own details once invited (no separate pre-boarding portal yet)
- [ ] P2 Welcome page (team, first-day plan, buddy)
- [ ] P2 Document packet to sign during onboarding
- [ ] P3 30/60/90-day check-in surveys

## Offboarding
- [x] P1 Offboarding flow: last day, reason, regretted, rehire eligibility, private note; reports move to the manager
- [x] P1 Offboarding checklist (handover, exit interview, equipment, access)
- [x] P2 Equipment marked returned
- [ ] P2 Exit interview survey
- [ ] P2 Turn off access through integrations (Google, Microsoft, Slack)
- [ ] P3 Alumni list

## Time off
- [x] P1 Leave types with yearly allowances (0 = no limit), paid or unpaid, colours
- [x] P1 Requests counted in working days (weekends and company holidays skipped), overlap and balance checks
- [x] P1 Approvals by anyone above the person, or HR; HR can enter leave for someone (auto-approved)
- [x] P1 Balances everywhere (home, profile, time off)
- [x] P1 Who's-out month calendar (leave type hidden from colleagues)
- [x] P1 Public holidays per company (Canada/Québec defaults, editable)
- [ ] P1 Accruals (per pay period, per hours worked) and prorating for mid-year starters
- [ ] P2 Carry-over, caps, waiting periods, expiry
- [ ] P2 Half days and hours
- [ ] P2 Manual balance adjustments with an audit trail
- [ ] P2 Calendar feed (iCal)
- [ ] P2 Blackout dates and minimum staffing warnings
- [ ] P3 Long leave with return-to-work tasks, time off in lieu

## Time and attendance
- [ ] P2 Clock in and out (web and phone)
- [ ] P2 Timesheets with weekly approval
- [ ] P2 Overtime rules, breaks
- [ ] P3 Shift scheduling, kiosk mode, project time

## Pay and compensation
- [x] P1 Pay record: rate, period (year, month, hour), currency, effective date; visible to the person, managers above them, HR
- [x] P1 Payroll export (CSV) for any period: pay, changes in the period, paid and unpaid days off
- [ ] P2 Payroll provider integrations (Gusto, ADP, Xero, QuickBooks)
- [ ] P2 Payslips uploaded for employees to view (files work today, no payslip section)
- [ ] P2 Salary bands, bonuses and one-off payments
- [ ] P3 Compensation review cycles, pay equity analysis, total-rewards statements, equity grants

## Benefits
- [ ] P2 Benefit plans and enrolments, dependants
- [ ] P3 Open enrolment, life events, carrier feeds

## Performance
- [x] P2 Review cycles: self + manager review for everyone, questions editable per cycle
- [x] P2 Ratings 1-5, drafts and submit; the person sees the manager review after the cycle closes
- [x] P2 Cycle progress for HR with the rating distribution, close a cycle
- [ ] P2 Peer / 360 feedback requests
- [ ] P2 Reminders for overdue reviews
- [ ] P3 Calibration (9-box), improvement plans, competency frameworks

## Goals
- [x] P2 Personal goals with progress, status and due date; managers see and edit their team's goals
- [ ] P2 Team and company goals with alignment
- [ ] P3 OKRs with key-result check-ins

## Feedback, 1:1s and recognition
- [x] P2 Kudos tied to company values (feed on home, performance and profiles)
- [ ] P2 1:1 agendas shared by manager and report
- [ ] P2 Private feedback

## Surveys and engagement
- [x] P2 eNPS pulse with optional comments, stored without names, shown after 3 answers
- [x] P2 eNPS trend in Reports
- [ ] P2 Custom pulse questions with other scales
- [ ] P3 Results by team (with anonymity thresholds), action plans

## Learning and training
- [ ] P2 Required training with due dates and completion tracking
- [ ] P3 Course library, certification expiry alerts, skills matrix

## Documents and e-signature
- [x] P1 Employee files (up to 8 MB, private to the person and HR)
- [x] P1 Company policies library
- [x] P2 Policy acknowledgements with who and when; editing a policy asks everyone again
- [ ] P2 Document templates with merge fields (offer, contract, letters)
- [ ] P2 E-signature with an audit certificate
- [ ] P3 Document expiry (visa, licence), employment verification letters

## Compliance and privacy
- [x] P1 Change history of every record (who, what, effective date) and a company audit log
- [x] P1 Full company export (JSON) for portability
- [~] P1 Delete people's records (offboarding keeps them; true erasure on request is manual today)
- [ ] P2 Retention rules (auto-delete candidates and former employees after N years)
- [ ] P2 Work permit / visa expiry tracking
- [ ] P2 Voluntary diversity fields (restricted access)
- [ ] P3 Incident log, anonymous reporting channel, country compliance packs

## Equipment
- [x] P2 Equipment register per person (kind, item, serial, given and returned)
- [ ] P2 Company-wide equipment list and stock
- [ ] P3 Equipment requests, software licences

## Expenses
- [ ] P3 Expense claims with receipt photos, approval and export

## Announcements and communication
- [x] P1 Company announcements on the home page (pinned first)
- [ ] P2 Targeted announcements (by team or location), read receipts
- [ ] P3 Comments and reactions, Slack/Teams posting

## Workflows and approvals
- [x] P1 One "Needs you" inbox: time off approvals, reviews, onboarding tasks, policies, the pulse
- [x] P1 Manager approval for time off
- [ ] P2 Employee change requests for HR-owned fields
- [ ] P2 Multi-step approval chains, delegation while on leave
- [ ] P2 Email reminders and a daily digest
- [ ] P3 No-code workflow builder, scheduled reminders (probation end)

## Reports and analytics
- [x] P1 Headcount, starting soon, on leave, turnover (12 months), new hires, regretted leavers
- [x] P1 Charts: headcount trend, hires and leavers, by team, location and type, tenure, time off by type, hiring funnel, eNPS
- [x] P1 CSV export of the people list (with or without pay)
- [ ] P2 Custom report builder (any field, filters, grouping)
- [ ] P2 Scheduled report emails
- [ ] P2 "As of" date reports
- [ ] P3 Pay equity and attrition analytics, natural-language questions

## Self-service and mobile
- [x] P1 Self-service: my profile, my time off, my tasks, my goals, policies to sign
- [x] P1 Every page works at phone width (tab bar, no sideways scroll)
- [x] P2 Manager view: team approvals, team goals, reviews to write
- [ ] P2 Installable app with push notifications
- [ ] P2 Notification preferences
- [ ] P3 HR helpdesk, AI assistant answering from the handbook, more languages (French first)

## Security and permissions
- [x] P1 Roles: HR admin, manager, employee (managers by reporting line)
- [x] P1 Managers see only the people below them
- [x] P1 Pay and personal details restricted by role (the server never sends hidden fields)
- [x] P1 Sign-in with email + password reset, and Continue with Google
- [x] P2 "Preview as" any colleague (HR), clearly flagged, no anonymous actions while previewing
- [ ] P2 Custom roles with field-level read/edit/none
- [ ] P2 Two-factor authentication
- [ ] P3 SAML SSO, SCIM provisioning, IP allowlists

## Integrations
- [ ] P2 Google Workspace / Microsoft 365 calendar sync
- [ ] P2 Slack/Teams notifications and approvals
- [ ] P2 Public REST API with keys, webhooks
- [ ] P3 Payroll and accounting connectors, Zapier

## Admin and settings
- [x] P1 Company setup in one screen, with a sample company to explore
- [x] P1 Teams, locations, company values
- [x] P1 Invite people with one-time links
- [x] P1 Leave types, holidays, onboarding and offboarding templates
- [x] P2 Full company data export
- [x] P3 Sample company data, removable in one click
- [ ] P2 Branding (logo, colours) on the careers page
- [ ] P2 Billing page with a clear per-person price
- [ ] P3 Several currencies and date formats per location
