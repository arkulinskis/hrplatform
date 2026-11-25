/* The main user journey, run inside the real app (Anvil App Server) by tools/ui_test.py through tools/live/drive.mjs.
   Resolves to {ok, log}. Keep log lines ASCII (the Windows console).
   Order: visitor pages -> sign up -> company setup (sample data) -> core pages (home, people, profile, org, view as)
   -> each page group's journey from tools/ui/flow_<area>.js (spliced in at the AREAS marker) -> theme + sign out. */
(async function () {
  const log = [], t0 = Date.now();
  const say = (m) => log.push(((Date.now() - t0) / 1000).toFixed(1) + 's ' + m);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function until(fn, what, ms) {
    const end = Date.now() + (ms || 20000);
    while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch (e) {} await sleep(150); }
    throw new Error('timed out waiting for: ' + what);
  }
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const byText = (sel, text) => $$(sel).find((e) => e.textContent.trim().replace(/\s+/g, ' ') === text);
  async function click(sel, text) {
    const el = await until(() => (text ? byText(sel, text) : $(sel)), sel + (text ? ' "' + text + '"' : ''));
    el.scrollIntoView({ block: 'center' });
    el.click();
    return el;
  }
  function type(input, value) {
    input.focus();
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  function pick(select, label) {  // Anvil DropDown values are internal: choose by the visible text
    const i = Array.from(select.options).findIndex((o) => o.text.trim() === label || o.text.indexOf(label) === 0);
    if (i < 0) throw new Error('no option ' + label);
    select.selectedIndex = i;
    select.dispatchEvent(new Event('change', { bubbles: true }));
  }
  async function page(hash, ready, what) {
    if (location.hash !== hash) window.UI_READY = false;  // the old page stays until the router runs
    location.hash = hash;
    await until(() => window.UI_READY && location.hash === hash && ready(), what || hash, 30000);
    await sleep(300);
  }
  const vis = (sel) => $$(sel).filter((e) => e.offsetParent !== null).pop();  // Anvil keeps closed dialogs in the page
  const ok = (cond, msg) => { if (!cond) throw new Error('FAILED: ' + msg); say('ok   ' + msg); };

  try {
    // ---- landing (visitors): the org chart draws itself
    await page('#landing', () => $('.lp-hero .hr-org-node'), 'landing');
    ok($('.lp-hero a[href="#auth/signup"]'), 'landing: hero with a sign-up link');
    ok($$('.lp-hero .hr-org-node').length >= 9, 'landing: the sample org chart is drawn');
    ok($('.ui-header .ui-btn.primary'), 'landing: Get started in the header');

    // ---- a members-only page sends visitors to sign in
    await page('#people', () => true);
    await until(() => window.UI_READY && $$('.au-card input').length >= 2, 'redirected to sign in');
    ok(true, 'a members-only page asks visitors to sign in');

    // ---- sign up -> no company yet -> setup
    await click('.au-card .ui-seg button', 'Create account');
    await until(() => $$('.au-card input[type=password]').length && $$('.au-card input').filter((i) => i.offsetParent).length >= 3, 'sign-up form');
    const inputs = $$('.au-card input[type=text], .au-card input[type=email], .au-card input[type=password]').filter((i) => i.offsetParent);
    type(inputs[0], 'Flow Tester'); type(inputs[1], 'flow' + Date.now() + '@example.com'); type(inputs[2], 'Hb-' + Math.random().toString(36).slice(2) + '-Kq7');
    const tick = $('.au-card input[type=checkbox]');
    if (tick && !tick.checked) tick.click();
    await click('.anvil-role-btn-block button', 'Create account');
    await until(() => window.UI_READY && $('.hr-setup'), 'company setup', 40000);
    ok(true, 'sign-up: a new account without a company lands on Set up your company');

    // ---- setup: create a workspace with the sample company
    await click('.hr-setup .anvil-role-btn-primary button');
    await until(() => /Give your company a name/.test($('.hr-setup').textContent), 'name required');
    ok(true, 'setup: a company name is required');
    type($('.hr-setup input'), 'Flow Robotics');
    await click('.hr-setup .anvil-role-btn-primary button');
    await until(() => location.hash === '#home' && window.UI_READY && $('.hr-hello'), 'home', 90000);
    ok(/Flow Robotics/.test($('.hr-hello').textContent), 'setup: workspace created, home shows the company');

    // ---- home
    ok($$('.hr-need').length >= 3, 'home: Needs you lists approvals, reviews and tasks (' + $$('.hr-need').length + ')');
    ok($$('.hr-home-stats .hr-stat').length === 5 && /\d/.test($('.hr-home-stats').textContent), 'home: HR numbers strip');
    ok($$('.hr-event').length >= 1, 'home: birthdays and anniversaries coming up');
    ok($$('.hr-ann').length >= 1, 'home: announcements');

    // ---- people directory: search, filter, open a profile
    await page('#people', () => $$('.hr-pcard').length > 20, 'people');
    const all = $$('.hr-pcard').length;
    type($('.hr-dir-head input'), 'priya');
    await until(() => $$('.hr-pcard').length === 1, 'search narrows the list');
    ok(/Priya Raman/.test($('.hr-pcard').textContent), 'people: search finds Priya');
    type($('.hr-dir-head input'), 'zzzz-nobody');
    await until(() => $('.ui-empty') && $('.ui-empty').offsetParent, 'empty state');
    ok(true, 'people: no match shows the empty state');
    type($('.hr-dir-head input'), '');
    pick($$('.hr-dir-head select')[0], 'Engineering');
    await until(() => $$('.hr-pcard').length > 2 && $$('.hr-pcard').length < all, 'team filter');
    ok($$('.hr-pcard').every((c) => /Engineering/.test(c.textContent)), 'people: team filter');
    pick($$('.hr-dir-head select')[0], 'All teams');
    await until(() => $$('.hr-pcard').length === all, 'filter cleared');
    $$('.hr-pcard').find((c) => /Kwame Mensah/.test(c.textContent)).click();
    await until(() => /^#person\//.test(location.hash) && window.UI_READY && $('.hr-profile-head'), 'profile', 30000);
    ok(/Kwame Mensah/.test($('.hr-profile-head').textContent) && /Reports to/.test($('.hr-profile-head').textContent), 'profile: name and manager');
    await click('.hr-tabs a', 'Job and pay');
    await until(() => $('.anvil-role-hr-pay') && $('.anvil-role-hr-pay').offsetParent, 'job tab');
    ok(/a year/.test($('.anvil-role-hr-pay').textContent), 'profile: HR sees pay on the Job and pay tab');

    // ---- change pay with an effective date, then see it in the history
    await click('.anvil-role-btn button', 'Change pay');
    const payBox = await until(() => vis('.hr-edit-person input[type=number]'), 'pay dialog');
    type(payBox, '151000');
    vis('.hr-edit-person .anvil-role-btn-primary button').click();
    await until(() => !vis('.hr-edit-person') && /151,000/.test(($('.anvil-role-hr-pay') || {}).textContent || ''), 'pay saved', 30000);
    ok(true, 'profile: pay change saved');
    await click('.hr-tabs a', 'History');
    await until(() => $$('.hr-hist').some((h) => /151000/.test(h.textContent)), 'history shows the change');
    ok(true, 'profile: the change history shows the new pay');

    // ---- my own profile: edit personal details
    await click('.anvil-role-avatar button');
    await click('.ui-menu a', 'My HR profile');
    await until(() => /^#person\//.test(location.hash) && window.UI_READY && /Flow Tester/.test(($('.hr-profile-head') || {}).textContent || ''), 'my profile');
    ok(/You/.test($('.hr-profile-head').textContent), 'my profile opens from the account menu');
    (await until(() => $$('.anvil-role-btn button').find((b) => b.offsetParent && /Edit my details/.test(b.textContent)), 'Edit my details')).click();
    const dlg = await until(() => { const d = vis('.hr-edit-person'); return d && d.querySelector('input[placeholder="e.g. she/her"]') && d; }, 'edit dialog');
    await sleep(500);
    const myHash = location.hash;
    type(dlg.querySelector('input[placeholder="e.g. she/her"]'), 'they/them');
    dlg.querySelector('.anvil-role-btn-primary button').click();
    await until(() => !vis('.hr-edit-person') || (dlg.querySelector('.anvil-role-msg-error') || {}).offsetParent, 'dialog closes', 30000);
    const err = dlg.querySelector('.anvil-role-msg-error');
    ok(!(err && err.offsetParent), 'my profile: Save closes the dialog ' + (err && err.offsetParent ? err.textContent : ''));
    await sleep(1500);
    await page('#people', () => $$('.hr-pcard').length > 5);
    await page(myHash, () => $('.hr-profile-head') && /Flow Tester/.test($('.hr-profile-head').textContent));
    ok(/they\/them/.test(document.body.textContent), 'my profile: the new pronouns are shown');

    // ---- add a person, then invite them
    await page('#people', () => $('.anvil-role-ic-plus button'));
    await click('.anvil-role-ic-plus button');
    await until(() => vis('.hr-add-person input'), 'add person dialog');
    vis('.hr-add-person .anvil-role-btn-primary button').click();
    await until(() => /first name/.test(vis('.hr-add-person').textContent), 'first name required');
    const ap = Array.from(vis('.hr-add-person').querySelectorAll('input')).filter((i) => i.type !== 'checkbox');
    type(ap[0], 'Wren'); type(ap[1], 'Okafor-Lindqvist'); type(ap[3], 'Support Specialist');
    vis('.hr-add-person .anvil-role-btn-primary button').click();
    await until(() => /^#person\//.test(location.hash) && window.UI_READY && /Wren Okafor-Lindqvist/.test(($('.hr-profile-head') || {}).textContent || ''), 'new profile', 30000);
    ok(true, 'add person: the new profile opens');
    await click('.anvil-role-btn button', 'Invite');
    const link = await until(() => vis('.hr-invite input'), 'invite dialog');
    ok(/#join\//.test(link.value), 'invite: a one-time join link');
    vis('.hr-invite .anvil-role-btn-ghost button').click();

    // ---- org chart: click a person
    await page('#org', () => $$('.hr-org-node').length > 20, 'org chart');
    ok($$('.hr-org-node.open').length >= 1, 'org chart: open roles shown dashed');
    $$('.hr-org-node:not(.open)').find((n) => /Lena Fischer/.test(n.getAttribute('aria-label'))).dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await until(() => /^#person\//.test(location.hash) && window.UI_READY && /Lena Fischer/.test(($('.hr-profile-head') || {}).textContent || ''), 'profile from chart');
    ok(true, 'org chart: selecting a person opens their profile');

    // ---- view as an employee (permission preview), then back
    await page('#more', () => $('.hr-more-grid'));
    pick($('.hr-section select'), 'Priya Raman');
    await click('.hr-section .anvil-role-btn button', 'Preview');
    await until(() => location.hash === '#home' && window.UI_READY && $('.hr-viewas') && $('.hr-viewas').offsetParent, 'view-as bar');
    ok(!$('.hr-home-stats') || !$('.hr-home-stats').offsetParent, 'view as: an employee sees no HR numbers');
    await click('.hr-viewas .anvil-role-btn button', 'Back to me');
    await until(() => window.UI_READY && !($('.hr-viewas') && $('.hr-viewas').offsetParent) && $('.hr-home-stats') && $('.hr-home-stats').offsetParent, 'back to HR view', 30000);
    ok(true, 'view as: Back to me restores the HR view');

    /*AREAS*/

    // ---- light / dark switch in the account menu
    await page('#home', () => $('.hr-hello'));
    await click('.anvil-role-avatar button');
    await click('.ui-menu .ui-seg button', 'Dark');
    ok(document.documentElement.classList.contains('ui-dark'), 'menu: Dark switches the theme');
    await click('.ui-menu .ui-seg button', 'Auto');

    // ---- sign out
    await click('.ui-menu button', 'Sign out');
    await until(() => location.hash === '#landing' && window.UI_READY && $('.ui-header .ui-btn.primary'), 'signed out');
    ok(true, 'sign out: back to the landing page as a visitor');

    say('PASSED');
    return { ok: true, log: log };
  } catch (e) {
    say(String(e && e.message || e));
    return { ok: false, log: log };
  }
})();
