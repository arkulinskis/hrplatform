/* hrseed.js: defines window.hrSeed() (it does not run anything by itself). tools/ui_test.py evaluates this before
   every script, so phone.js, a11y.js, design.js and the screenshots share one way to get a signed-in HR admin of a
   company with sample data, plus ids for the pages that need one.
   window.hrSeed(name) -> {person, job, checklist, review, policy, cycle, member: [every member page address]} */
window.hrSeed = async function (name) {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function until(fn, what, ms) {
    const end = Date.now() + (ms || 30000);
    while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch (e) {} await sleep(150); }
    throw new Error('timed out waiting for: ' + what);
  }
  const $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  function type(input, value) {
    input.focus(); input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  async function go(hash, ready) {
    if (location.hash !== hash) window.UI_READY = false;
    location.hash = hash;
    await until(() => window.UI_READY && location.hash === hash && (!ready || ready()), hash, 40000);
    await sleep(250);
  }
  const first = (sel) => { const a = $(sel); return a ? a.getAttribute('href') : null; };
  if (location.hash !== '#auth/signup') window.UI_READY = false;
  location.hash = '#auth/signup';
  await until(() => window.UI_READY && $$('.au-card input').length >= 3, 'sign-up');
  const inputs = $$('.au-card input[type=text], .au-card input[type=email], .au-card input[type=password]');
  type(inputs[0], name || 'Sam Rivera'); type(inputs[1], 'seed' + Date.now() + Math.floor(Math.random() * 1000) + '@example.com');
  type(inputs[2], 'Hb-' + Math.random().toString(36).slice(2) + '-Kq7');
  const tick = $('.au-card input[type=checkbox]'); if (tick && !tick.checked) tick.click();
  $$('.anvil-role-btn-block button').find((b) => /Create account/.test(b.textContent)).click();
  await until(() => window.UI_READY && $('.hr-setup'), 'company setup page', 60000);
  type($('.hr-setup input'), 'Northwind Bakery Co-op');
  $$('.hr-setup button').find((b) => /Create my workspace/.test(b.textContent)).click();
  await until(() => location.hash === '#home' && window.UI_READY && $('.hr-hello'), 'home with sample data', 90000);
  const S = {};
  await go('#people', () => $$('.hr-pcard').length > 5);
  S.person = $$('.hr-pcard').map((a) => a.getAttribute('href')).find((h) => h && !/#person\/?$/.test(h));
  try { await go('#hiring', () => $('a[href^="#job/"]')); S.job = first('a[href^="#job/"]'); } catch (e) {}
  try { await go('#onboarding', () => $('a[href^="#checklist/"]')); S.checklist = first('a[href^="#checklist/"]'); } catch (e) {}
  try { await go('#performance', () => $('a[href^="#review/"]')); S.review = first('a[href^="#review/"]'); S.cycle = first('a[href^="#cycle/"]'); } catch (e) {}
  try { await go('#docs', () => $('a[href^="#policy/"]')); S.policy = first('a[href^="#policy/"]'); } catch (e) {}
  S.member = ['#home', '#people', S.person, '#org', '#timeoff', '#timeoff/calendar', '#timeoff/approvals', '#hiring',
    S.job, '#onboarding', S.checklist, '#performance', '#performance/goals', '#performance/kudos', '#performance/pulse',
    S.review, S.cycle, '#docs', S.policy, '#reports', '#settings', '#settings/time', '#more', '#profile'].filter(Boolean);
  window.SEED = S;
  await go('#home', () => $('.hr-hello'));
  return S;
};
1;
