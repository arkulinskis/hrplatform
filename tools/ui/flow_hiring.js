    // ================================================================ hiring (Pages/Hiring, Job, Careers) + onboarding (Pages/Onboarding, Checklist)
    {  // own block: names here never clash with the other page groups' journeys
    const hv = (el) => !!(el && el.offsetParent);
    const btnBy = (scope, re) => $$(scope + ' button').find((b) => hv(b) && re.test(b.textContent.trim()));

    // ---- hiring overview: jobs with pipeline strips, careers link, new applications
    await page('#hiring', () => $$('.hi-job').length >= 3, 'hiring');
    ok($$('.anvil-role-hi-jobs .hi-job').length >= 4, 'hiring: HR sees every job (' + $$('.anvil-role-hi-jobs .hi-job').length + ')');
    ok(/Senior Backend Engineer/.test($('.hi-jobs-box').textContent), 'hiring: sample job listed');
    ok($$('.hi-strip').length >= 4 && /Applied/.test($('.hi-strip').textContent), 'hiring: pipeline strip per job');
    const careersUrl = $('.anvil-role-hi-url').textContent.trim();
    ok(/#careers\/[\w-]+$/.test(careersUrl), 'hiring: careers page link shown (' + careersUrl.split('#')[1] + ')');
    ok($('.hi-careers-url').getAttribute('target') === '_blank', 'hiring: careers link opens in a new tab');
    ok($$('.anvil-role-hi-recent .hr-prow').length >= 1, 'hiring: new applications listed');
    btnBy('.hi-filter', /^Drafts/).click();
    await until(() => $$('.anvil-role-hi-jobs .hi-job').length === 1 && /Product Designer/.test($('.anvil-role-hi-jobs').textContent), 'drafts filter');
    ok(true, 'hiring: Drafts filter shows the draft job only');
    btnBy('.hi-filter', /^All/).click();
    await until(() => $$('.anvil-role-hi-jobs .hi-job').length >= 4, 'all jobs again');
    await click('.hi-careers-box .anvil-role-ic-copy button');
    ok(true, 'hiring: Copy link pressed');

    // ---- new job through the dialog -> its pipeline opens
    await click('.ui-page-head .anvil-role-btn-primary button');
    await until(() => $('.hi-jobedit input'), 'job dialog');
    await click('.hi-jobedit .anvil-role-btn-primary button');
    await until(() => /Give the job a title/.test($('.hi-jobedit').textContent), 'title required');
    ok(true, 'new job: a title is required');
    type($('.hi-jobedit input'), 'Flow Test Engineer');
    type($('.hi-jobedit input[placeholder*="CAD"]') || $$('.hi-jobedit input')[1], '80k-90k');
    type($('.hi-jobedit textarea'), 'Line one\nLine two');
    await click('.hi-jobedit .anvil-role-btn-primary button');
    await until(() => /^#job\//.test(location.hash) && window.UI_READY && $('.hi-board') && /Flow Test Engineer/.test($('.hi-jobhead').textContent), 'job page', 30000);
    ok($$('.hi-col').length === 6, 'job: six stage columns on the board');
    ok($('.hi-board').getAttribute('tabindex') === '0' && $('.hi-board').getAttribute('aria-label'), 'job: board scrolls in its own focusable box');
    ok(/no interviews|New applications land here/i.test($('.hi-board').textContent), 'job: empty columns explain themselves');

    // ---- add a candidate, move them on with Next
    await click('.hi-jobhead-actions .anvil-role-ic-plus button');
    await until(() => $('.hi-addcand input'), 'add candidate dialog');
    type($('.hi-addcand input'), 'Zoe Flowtest');
    type($$('.hi-addcand input')[1], 'zoe.flowtest@example.com');
    await click('.hi-addcand .anvil-role-btn-primary button');
    await until(() => !$('.hi-addcand') && $$('.hi-col.k-applied .hi-card').some((c) => /Zoe Flowtest/.test(c.textContent)), 'candidate added', 30000);
    ok(true, 'add candidate: lands in Applied');
    const zoe = () => $$('.hi-card').find((c) => /Zoe Flowtest/.test(c.textContent));
    zoe().querySelector('.anvil-role-ic-arrow button').click();
    await until(() => $$('.hi-col.k-screen .hi-card').some((c) => /Zoe Flowtest/.test(c.textContent)), 'moved to screen', 30000);
    ok(true, 'board: Next moves the candidate to Phone screen');
    ok(document.activeElement && document.activeElement.closest && document.activeElement.closest('.hi-card') && /Zoe Flowtest/.test(document.activeElement.closest('.hi-card').textContent), 'board: keyboard focus follows the moved card');

    // ---- candidate dialog: rate, note, hire
    zoe().querySelector('.hi-card-open').click();
    await until(() => $('.hi-cand') && /Zoe Flowtest/.test($('.hi-cand').textContent) && $$('.hi-stars button').length === 5, 'candidate dialog');
    ok(/zoe\.flowtest@example\.com/.test($('.hi-cand-kv').textContent), 'candidate: email shown');
    $$('.hi-stars button').find((b) => b.textContent.trim() === '4').click();
    await until(() => $$('.hi-stars button').find((b) => b.textContent.trim() === '4').getAttribute('aria-pressed') === 'true', 'rated 4');
    ok(/Rated 4 out of 5/.test($('.hi-cand-rate').textContent), 'candidate: rating saved (aria-pressed)');
    type($('.hi-note-field textarea'), 'Great call, strong on testing.');
    await click('.hi-cand button', 'Add note');
    await until(() => $$('.hi-note').some((n) => /strong on testing/.test(n.textContent)), 'note added', 30000);
    ok($$('.hi-note.sys').length >= 1, 'candidate: notes timeline with quieter system notes');
    await click('.hi-cand .anvil-role-ic-award button');
    await until(() => hv($('.hi-hire')) && $('.hi-hire input').value.length === 10, 'hire form');
    ok($('.hi-hire input').type === 'date', 'hire: start date picker');
    await click('.hi-hire button', 'Confirm hire');
    await until(() => hv($('.hi-hired')) && /is hired/.test($('.hi-hired').textContent), 'hired', 40000);
    ok(/#person\//.test($('.hi-hired-link').getAttribute('href')), 'hire: link to the new profile');
    ok(!hv($('.hi-cand .anvil-role-ic-award button')), 'hire: no second Hire button once hired');
    await click('.hi-cand button', 'Done');
    await until(() => !$('.hi-cand') && $$('.hi-col.k-hired .hi-card').some((c) => /Zoe Flowtest/.test(c.textContent)), 'board shows hired', 30000);
    ok(true, 'board: the hired candidate sits in Hired');

    // ---- close the job: off the careers page
    btnBy('.hi-status', /^Closed$/).click();
    await until(() => /Closed: no longer/.test($('.hi-desc-box').textContent), 'job closed', 30000);
    ok(true, 'job: status buttons close the job');

    // ---- public careers page: open a job, apply
    const careersHash = '#' + careersUrl.split('#')[1];
    await page(careersHash, () => hv($('.hi-careers')) && $$('.hi-cjob').length >= 1, 'careers page');
    ok(/Careers at Flow Robotics/.test($('.hi-careers-head').textContent), 'careers: company name as the title');
    ok(!/Flow Test Engineer/.test($('.anvil-role-hi-cjobs').textContent), 'careers: closed jobs are not listed');
    $('.hi-cjob-sum').click();
    await until(() => $('.hi-cjob[open]'), 'job opened');
    ok(getComputedStyle($('.hi-cjob[open] .anvil-role-hi-desc')).whiteSpace === 'pre-line', 'careers: description keeps line breaks');
    $('.hi-cjob[open] .anvil-role-btn-primary button').click();
    await until(() => $('.hi-apply input'), 'apply dialog');
    const hp = $('.hi-hp input');
    ok(hp && hp.getAttribute('tabindex') === '-1' && hp.getAttribute('autocomplete') === 'off', 'apply: hidden honeypot field');
    await click('.hi-apply button', 'Send application');
    await until(() => /Add your name/.test($('.hi-apply').textContent), 'name required');
    ok(true, 'apply: name required');
    const ap = $$('.hi-apply input').filter((i) => hv(i));
    type(ap[0], 'Flow Applicant'); type(ap[1], 'flow.applicant' + Date.now() + '@example.com');
    type($('.hi-apply textarea'), 'I would love to join.');
    await sleep(2700);  // the server ignores forms sent faster than a person could
    await click('.hi-apply button', 'Send application');
    await until(() => hv($('.hi-apply-done')) && /Thanks! The team will be in touch/.test($('.hi-apply-done').textContent), 'application sent', 30000);
    ok(true, 'apply: success message');
    await click('.hi-apply button', 'Back to the jobs');
    await page('#careers/larkspur', () => hv($('.hi-careers')) && /Larkspur/.test($('.hi-careers-head').textContent), 'sample careers page');
    ok(hv($('.hi-demo-note')), 'careers: the sample company says it is a sample');
    await page('#careers/no-such-company-zz', () => hv($('.hi-careers-missing')), 'unknown careers page');
    ok(true, 'careers: unknown link shows a friendly not-found page');
    await page('#hiring', () => $$('.anvil-role-hi-recent .hr-prow').length >= 1, 'hiring again');
    ok(/Flow Applicant/.test($('.hi-recent-box').textContent), 'hiring: the application shows under New applications');

    // ---- onboarding overview: my tasks, checklists, start one
    await page('#onboarding', () => hv($('.ob-page')) && $$('.hr-clcard').length >= 2, 'onboarding');
    ok(/Welcome Zoe Flowtest/.test($('.ob-page').textContent), 'onboarding: hiring created the onboarding checklist');
    ok(/Offboarding/.test($('.ob-page').textContent) && $('.ob-page a[href="#settings/checklists"]'), 'onboarding: sections + link to the templates');
    ok($$('.ob-tasks-box .ob-task').length >= 1, 'onboarding: Your tasks listed (' + $$('.ob-tasks-box .ob-task').length + ')');
    const myBox = $$('.ob-tasks-box .ob-task input[type=checkbox]').find((i) => !i.disabled && !i.checked);
    const myRow = myBox.closest('.ob-task');
    myBox.click();
    await until(() => myRow.classList.contains('done') && /Done by/.test(myRow.textContent), 'task ticked', 30000);
    ok(true, 'onboarding: ticking a task marks it done with who did it');
    pick($('.ob-start select'), 'Priya Raman');
    pick($$('.ob-start select')[1], 'Onboarding');
    await click('.ob-start button', 'Start checklist');
    await until(() => /^#checklist\//.test(location.hash) && window.UI_READY && /Welcome Priya Raman/.test(($('.ob-head') || {}).textContent || ''), 'new checklist', 30000);
    ok(true, 'start checklist: opens the new checklist');

    // ---- checklist page: progress, groups, add / tick / delete a task
    ok($('.ob-bar[role=progressbar]') && /0 of \d+ done/.test($('.ob-progress').textContent), 'checklist: progress bar starts at 0');
    ok($$('.ob-group').filter(hv).length >= 2, 'checklist: tasks grouped by role');
    ok($('.ob-person-link').getAttribute('href').indexOf('#person/') === 0, 'checklist: links to the person');
    const total0 = +(/of (\d+) done/.exec($('.ob-progress').textContent)[1]);
    type($('.ob-add input'), 'Flow test task');
    pick($('.ob-add select'), 'IT');
    await click('.ob-add button', 'Add task');
    await until(() => $$('.ob-group .ob-task').some((r) => /Flow test task/.test(r.textContent)) && new RegExp('of ' + (total0 + 1) + ' done').test($('.ob-progress').textContent), 'task added', 30000);
    ok(true, 'checklist: HR adds a task');
    const ftRow = () => $$('.ob-group .ob-task').find((r) => /Flow test task/.test(r.textContent));
    ftRow().querySelector('input[type=checkbox]').click();
    await until(() => /^1 of/.test($('.ob-progress .anvil-role-strong').textContent.trim()), 'progress moves', 30000);
    ok(ftRow().classList.contains('done'), 'checklist: ticking updates the progress bar');
    ftRow().querySelector('.anvil-role-ic-trash button').click();
    await click('.anvil-modal-content button', 'Delete');
    await until(() => !ftRow() && new RegExp('of ' + total0 + ' done').test($('.ob-progress').textContent), 'task deleted', 30000);
    ok(true, 'checklist: delete asks, then removes the task');
    }
