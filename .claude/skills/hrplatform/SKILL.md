---
name: hrplatform
description: Context, workflow and recipes for HR Platform (folder hrplatform), the user's Anvil app built as native Anvil Forms (Python + HTML templates, a layout, custom components, RepeatingPanels). An HR workspace for small companies (BambooHR-style): people records with field-level privacy and effective-dated history, org chart, time off, hiring + public careers page, onboarding/offboarding, reviews, goals, kudos, anonymous eNPS, policies, reports and payroll export. Load this before any feature request, bug fix, restyle, content change or deploy for this app.
---

# HR Platform: working on the app

**What it is:** a multi-company HR workspace. Each company is private; the creator is its HR admin and invites
everyone else with one-time links. Three sides: HR admins (everything), managers (people below them in the reporting
line: approvals, reviews, team goals, pay) and employees (self-service). Core loop: HR keeps one record per person;
every area (time off, hiring, onboarding, performance, policies, reports) hangs off that record; the home page's
"Needs you" inbox gathers what each person must do. README.md lists every feature; BACKLOG.md what's next.

**Where it lives:**
- Folder `C:\Users\arkvi\Documents\CLAUDE\hrplatform\` = the git clone of **github.com/arkulinskis/hrplatform**, branch `master`.
  "git" layout: the folder *is* the Anvil app. Anvil pulls master; pushing is the deploy. Live: https://hr-platform.anvil.app (app id KDAE63RLZGA32RE2).
- Made from `C:\Users\arkvi\Documents\CLAUDE\APP_MAKER\template-forms` (native Anvil Forms, Nov 2026). Anvil's own agent
  skills describe the same model: `client-forms`, `data-models`, `server-code`, `client-modules`, `anvil-yaml`
  (github.com/anvil-works/anvil-agent-references; see APP_MAKER/ANVIL_NOTES.md, "Native Anvil Forms").
- **README.md** lists every feature. Keep it up to date.

**What the user wants:** "Calm ledger" (chosen 2026-11-25): ledger-paper page #f6f5f1, white surfaces, ink #1f2421,
spruce #2f6b4f for actions, amber #d98e3a only as a highlight (#8a5210 as text); dark bg #141816. Bricolage Grotesque
headings, Source Sans 3 body; 10px radius, hairline borders, soft one-layer shadows; six avatar/leave tones
(`--tone-0..5-bg/fg`, `lv-<colour>`). Landing = Persuade (the org chart draws itself); app = Operate. Loader: stitch.
The user asked for research-led features, a categorised backlog and an explanation artifact. Claude assumes
details and builds; Claude deploys. Mobile-first: every page must fit 390 px. Light and dark.

## Workflow for any change

1. `git pull --ff-only` (Anvil commits "Edited ..." when the user changes something in the IDE; read those commits).
2. Edit: a page's template and Python side by side (`client_code/Pages/X/form_template.html` + `__init__.py`).
3. `python tools/check.py` (no -I) -> **ALL CHECKS PASSED**: Anvil's validator (`anvil validate`, type-checks every
   template and Python file against Anvil's API), JS syntax, asset hashes (`tools/assets.py`), server tests.
   Needs the Anvil CLI once: `npm install -g @anvil-works/anvil-cli`.
4. `python -I tools/ui_test.py` (Docker Desktop running) -> **ALL UI TESTS PASSED**: the folder runs as-is in the
   open-source Anvil App Server (container `hrplatform-dev`) and headless Chrome walks tools/ui/flow.js, phone.js
   (true 390 px, no sideways scroll), admin.js and a11y.js (axe-core WCAG 2.2 AA on every page, light + dark, plus
   keyboard checks). Client edits show on reload; server edits need `--restart`. `--only a11y.js` runs one script.
   `--shots DIR` = screenshots of every page, desktop + phone, light + dark, guest + member: Read them.
5. Commit only your files as arkulinskis with the Co-Authored-By line; `git push origin master`.
   New tables/columns: tell the user to accept the **Schema Mismatch** alert ("The schema of the source code is correct").

## Architecture

```
anvil.yaml                 startup: module `startup`; db_schema; services; head_html (fonts, Prepsto, theme assets with ?v=)
client_code/
  startup.py               get_me, Privacy & Terms kit, router.start()
  session_guard.py         expired server session -> quiet reload at the same address (start() first in startup.py);
                           server_code/KeepAlive.py session_ping; test: python -I tools/session_test.py
  router.py                PAGES (who may open each page), NAV (main menu), _form (page -> Form), go/href/replace
  state.py                 me(), call() (expected {"ok": False} -> toast + None), toast(), store, set_attr, dates
  auth.py                  sign in / up / reset / Continue with Google / sign out
  legal.py                 Privacy & Terms (installed from APP_MAKER/legal-kit; don't edit here)
  Layouts/Shell            header + account menu + footer + phone tab bar; slot "content"; refresh(page)
  Pages/                   Landing, Auth, Home (EXAMPLE), Profile, Admin (overview, feedback, users, demo data)
  Components/              custom components (Initials = the example); wrap any JS engine here
  Items/                   RepeatingPanel item templates: NavLink, ItemCard (EXAMPLE), FeedbackRow, UserRow
  Dialogs/                 dialog Forms for alert(): AddItem (EXAMPLE)
server_code/               common.py (C.*), Accounts, Admin, DemoData, Feedback, ExampleItems (EXAMPLE), SchemaCheck
theme/assets/              app.css (tokens + pages + the role layer), icons.css (generated), app-kit.js, theme.css
                           (loading spinner), icon.svg + PNGs (tools/make_icons.py)
tools/                     check.py, assets.py, build_icons.py, make_icons.py, ui_test.py + ui/, live/drive.mjs, testing/
```

## How things are done here

- **Page** = `client_code/Pages/X/` with `<anvil-form layout="HR_Platform.Layouts.Shell"><anvil-block slot="content">`
  and `class X(XTemplate)` taking `args=()` (the URL parts after `#x/`). Register it in router.py: `PAGES`, `_form`,
  and `NAV` if it belongs in the menu (max 4). Add its address to tools/ui/phone.js and its journey to flow.js.
- **The layout is reused between pages** (open_form keeps the Shell when the layout matches): anything in the Shell
  that depends on the user or the page goes in `Shell.refresh(page)`.
- **Navigation** = plain `<a href="#page">`; in code `router.go("page", arg)`; build links with `router.href`.
- **Static copy** = plain HTML in the template. **Text that changes** = a `Label` (role for the look).
- **Actions** = Anvil `Button` + `@handle("name", "click")`, roles `["btn", "btn-primary", "ic-plus"]`. Button roles
  are aliases of `.ui-btn` in app.css: `btn-primary`, `btn-ghost`, `btn-danger` + `btn-solid`, `btn-sm`, `btn-lg`,
  `btn-icon`, `btn-block`. Icons: role `ic-<name>` on Buttons/Links, `<i class="ic ic-<name>">` in HTML
  (names in app-kit.js `UI.ICONS`; add one there and run tools/build_icons.py).
- **Inputs** = TextBox / TextArea / DropDown / CheckBox (styled by app.css through `.ui input`, `.ui textarea`).
  Read `.text` / `.selected_value` / `.checked`; `pressed_enter` for Enter.
- **Plain HTML that changes** = `anvil:name="x"`, then `self.x.visible`, `self.x.classes["on"] = ...`,
  `self.x.style[...]`; attributes with `state.set_attr(self.x, "href", ...)`. Native clicks:
  `anvil:on-dom:click="self.x_click"` + `def x_click(self, event)`.
- **Lists** = `RepeatingPanel` + an `Items/` Form; never build repeated HTML strings. Bind fields in the item template
  (`bind:text="self.item['title']"`). Grid/flex CSS goes on the panel's items container: `.anvil-role-<role> > div`.
  Item -> page: `self.parent.raise_event("x-something", ...)` + `panel.add_event_handler("x-something", ...)`.
  Role `contents` lets a panel's items join the surrounding grid.
- **Dialogs** = a Form in `Dialogs/`, `alert(Form(...), buttons=[], role="app-dialog")`; it closes itself with
  `self.raise_event("x-close-alert", value=...)`. Yes/no: `confirm(text, title=..., buttons=[("Cancel", False), ("Delete", True)])`.
- **Toasts** = `state.toast(msg, "ok" | "error")` (Anvil Notification with roles).
- **Server calls** = `state.call("fn", ...)` for normal flows (expected `{"ok": False, "error"}` -> toast, returns None);
  a page that shows a friendly state instead (not found, private) calls `anvil.server.call` and checks `ok` itself.
  Server functions: `@anvil.server.callable(require_user=True)`, `C.require_user()` / `C.require_admin()`, ownership
  checks, return plain dicts (`C.ok(...)` / `C.fail("...")`), never other people's emails. Tables are `client: none`.
- **JavaScript** only for engines Python is too slow for (canvas, SVG drawing, WebGL, audio, maps, PDF): put it in
  `theme/assets/<name>.js`, load it in head_html (then `python tools/assets.py`), wrap it in one Python module
  (`from anvil.js import window`) and/or a `Components/` custom component. Little Hero Books is the worked example.

- **Accessibility (WCAG 2.2 AA, the legal bar; 2026-11-04)**: tools/ui/a11y.js runs axe-core on every page (light +
  dark, guest + member) and fails on serious problems; add new pages to its PUBLIC/MEMBER lists. The rules:
  - Text colours reach 4.5:1 on every surface: check new tokens (`--c-faint`, `--c-accent` used as text, status
    colours on their `-soft` fills). Text on good/bad/warn fills is `var(--c-on-status)` (white light, ink dark).
  - Every field has a name: wrap it in `<label class="ui-field"><span>Caption</span>...</label>`, or
    `state.set_control_attr(box, "aria-label", "...")` when the caption isn't a label (set it AFTER `.items` on a
    DropDown: Anvil rebuilds the select). Name/email/phone/password get `autocomplete` (set_control_attr).
  - The page's title Label is a heading: `state.heading(label, 1)` (one per page; Labels render as divs).
  - Toggle buttons say they're on: `.ui-seg` buttons get aria-pressed from the "on" class automatically (app-kit.js);
    elsewhere `state.set_control_attr(btn, "aria-pressed", ...)`. Never `role="tablist"` without real tabs.
  - Messages that appear are read out: roles msg-error/msg-note get role alert/status automatically; other changing
    Labels: `state.live(label)`. Hidden text just for screen readers: Label role `sr`.
  - When a click redraws a RepeatingPanel, keep the keyboard's place: give the item's button a `data-key` and call
    `state.refocus(panel, key)` after the event (PlanPlate's Items/Chip). Buttons have no `.focus()`: `state.focus(btn)`.
  - Images: content images get real alt text (photos: their caption); decorative ones `alt=""`; a Button icon image
    is set to alt="" automatically. Hidden anti-spam fields: `tabindex=-1`, `autocomplete=off`.

- **Design kit (2026-11-05)**: `APP_MAKER/design/README.md` is the bar for every visual change (craft floor, the
  "AI-made" tells, motion rules, worst-case data). app.css carries its CSS between `design-kit:start/end` (easing and
  duration tokens, browser surfaces, text wrapping, press feedback, gentle reduced motion): every transition uses
  `--ease-*` / `--dur-*`, no `ease-in`, no `transition: all`, no eyebrow labels, no gradient text. Checks:
  `python -I APP_MAKER/tools/design_check.py hrplatform` (source; check.py prints its summary) and tools/ui/design.js
  (rendered, desktop + phone, inside ui_test.py; add new pages to its PUBLIC/MEMBER). Deliberate exceptions:
  `design-ok: <rule>` comment on the line.

## Recipes

- **New table or column:** `db_schema` in anvil.yaml (same shape as the existing tables, `client: none`), then add it
  to server tests. Deploy, then the Schema Mismatch step. Personal data -> the legal kit (below).
- **New server function:** in a server module + tests in tools/testing/test_server.py (happy path, bad input,
  someone not allowed; public ones in `PUBLIC`).
- **Demo content:** DemoData.py (`is_demo=True`, `DEMO_TABLES`, children first).
- **Restyle:** tokens at the top of app.css (light and dark blocks), fonts in head_html, the spinner in theme.css
  (`python -I APP_MAKER/tools/loaders.py apply hrplatform <preset>`), `LEGAL_THEME` in startup.py.
- **Icon:** edit theme/assets/icon.svg, `python -I tools/make_icons.py`, then `python tools/assets.py`.

## Gotchas

- The local App Server (1.18) lags hosted Anvil: no `HtmlComponent.attrs` (use state.set_attr), `Notification(role=)`
  raises (state.toast falls back), notifications are `.anvil-alert[data-notify]`, components are wrapped in
  `<anvil-dropzone>` (app.css: `display: contents`). app.css styles both. Test on hosted Anvil too for big changes.
- Anvil's alert() without `large=True` is a 300 px modal: our role `app-dialog` widens it.
- Headless Chrome: Anvil's service worker breaks reused profiles (drive.mjs bypasses it); phone width needs device
  emulation (`MOBILE=390,844`), windows can't go below ~500 px.
- `require_secure_passwords` rejects leaked passwords: tests use random ones.
- Heredocs in the Bash tool mangle quotes: write files with the Write tool.
- A script's `el.focus()` doesn't always match `:focus-visible`, so tests check focus rings through the CSS rules,
  not computed styles. Never put `outline: none` on `input:focus` without `:not([type=checkbox]):not([type=radio])`.
- Never write Anvil's theme-colour token pattern (percent, `color:`, name, percent) in theme.css.

## Privacy & Terms (legal kit)

From `C:/Users/arkvi/Documents/CLAUDE/APP_MAKER/legal-kit`: change `apps/hrplatform.json`, then there
`python -I build.py hrplatform && python -I install.py hrplatform` (writes theme/assets/legal-kit.js,
client_code/legal.py, server_code/legal_server.py and the head_html tag), then `python tools/assets.py` and deploy.
Sign-up keeps the tick box (`legal.consent_field()` in Pages/Auth). Feedback = Prepsto only ("Submit feedback").
- Client and server modules share ONE Python package: a server module can't have the same name as a client
  package or module (server `Items.py` + client `Items/` = "Cannot resolve imported module"). The template's example
  server module is `ExampleItems.py` for that reason.

## HR Platform specifics

**Permission model (server, one place: `server_code/Workspace.py`).** Every callable starts `cx = W.ctx()` (user,
company, real employee `cx.me`, effective employee `cx.emp` = view-as target, `cx.is_admin`). Rules:
`can_private` (person or HR: personal details, files, equipment, history), `can_pay`/`can_team` (person, managers above
them, HR: pay, balances, goals), HR only for job fields, notes, settings. `W.full(e, cx)` only includes the fields the
viewer may see, so the client never receives hidden data. Rows are always checked against `cx.company`
(`W.emp_in`, `W.row_in`). Roles live on the employee row (`role`: admin / manager / employee); "manager" also means
anyone with reports. Site admin (`users.is_admin`, App Secret) is separate from company HR.

**View as.** `view_as(emp_id)` stores the target in the session for a real HR admin; `ctx()` then acts as them
(including permissions). Anonymous or personal actions (pulse answers, policy acknowledgements) refuse while previewing.
`get_me` returns `viewing_as`, `role` (effective) and `real_role`; the Shell shows the yellow bar.

**Data shapes.** Server replies are plain dicts (`W.card`, `W.full`, `Leave._req`, `Hiring._cand` ...). Effective-dated
changes are rows in `changes` (kind personal/job/pay/status/notes/system). Pulse answers have NO employee column
(`survey_done` records who answered): keep it that way.

**Sample data.** `Sample.seed(company, me)` builds a 26-person fictional company relative to today (leave, jobs and
candidates, checklists, an open review cycle, goals, kudos, two pulses, policies with acks, announcements, equipment)
with add_rows batches (Anvil's 30 s limit). `Sample.remove(company)` deletes sample rows and real rows pointing at them.
Leave types and holidays are real defaults (`Sample.defaults`). `DemoData` = the public demo company "Larkspur
Studio" (`#careers/larkspur`), loaded on the first careers-page visit, managed in Site admin.

**Engines.** `theme/assets/hr-engines.js`: `HR.orgChart` (tidy tree, big leaf teams stack vertically, `animate` for
the landing), `HR.chart` (bar/hbar/line), `HR.calendar` (who's out), `HR.download`, `HR.copy`. Wrapped by
Components/OrgChart, Chart, MonthCalendar (draw on `show` and when `data` changes).

**Recipes.**
- New field on a person: column in anvil.yaml `employees`, `Staff.PERSONAL/JOB/PAY` + `LABELS`, `W.full` (in the right
  permission block), Dialogs/EditPerson (field + `_data`), Pages/Person (display), Reports exports if relevant, legal kit.
- New "Needs you" kind: add it in `Dashboard.get_home` (`kind`, `icon`, `title`, `sub`, `href`) + a colour in hr.css
  `.hr-need-ic.k-<kind>`.
- New page group CSS goes in its own `theme/assets/hr-<area>.css` (linked in head_html; run `python tools/assets.py`).
- UI tests: `tools/ui/flow.js` (core) splices every `tools/ui/flow_<area>.js` at `/*AREAS*/`; `tools/ui/hrseed.js`
  defines `window.hrSeed()` (sign up + company with sample data + ids for id pages), used by phone/a11y/design/shots.

**Gotchas.**
- Sign-up lands on #setup (no company yet), not #home: tests and redirects must allow it.
- `router.PAGES` "member" = signed in AND in a company; `state.in_company()`.
- Dates from the client are 'YYYY-MM-DD' text (TextBox type=date); servers parse with `date.fromisoformat`.
- Time off `days` excludes weekends + company holidays; allowance 0 = unlimited.
