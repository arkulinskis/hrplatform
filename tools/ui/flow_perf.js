    // ================================================================ performance, policies and news, reports
    // (Pages/Performance, Review, Cycle, Docs, Policy, Reports). Signed in as the HR admin with sample data.
    const pvis = (el) => !!(el && el.offsetParent);
    const ptext = (sel) => ($(sel) || { textContent: '' }).textContent.replace(/\s+/g, ' ');
    const modalBtn = (text) => click('.anvil-modal-content button', text);
    const stamp = String(Date.now()).slice(-6);

    // ---- reviews tab: HR sees cycles; start a cycle through the dialog
    await page('#performance/reviews', () => pvis($('.pfx-reviews')) && pvis($('.anvil-role-pfx-cycles')), 'performance: reviews');
    ok($('.ui-tabs a.on') && /Reviews/.test($('.ui-tabs a.on').textContent), 'performance: Reviews tab is on');
    ok(pvis($('.anvil-role-pfx-write-list')) || /Nothing to write/.test(ptext('.pfx-reviews')), 'performance: reviews to write (or empty line)');
    await click('.pfx-reviews button', 'Start a review cycle');
    await until(() => $('.pfx-dlg-cycle textarea') && $('.pfx-dlg-cycle textarea').value.split('\n').length >= 3, 'start cycle dialog');
    ok(/went well/.test($('.pfx-dlg-cycle textarea').value), 'start cycle: default questions prefilled');
    ok($('.pfx-dlg-cycle input[type=date]') && /^\d{4}-\d{2}-\d{2}$/.test($('.pfx-dlg-cycle input[type=date]').value), 'start cycle: due date prefilled');
    type($('.pfx-dlg-cycle input'), 'Flow cycle ' + stamp);
    await click('.pfx-dlg-cycle button', 'Start the cycle');
    await until(() => window.UI_READY && /^#cycle\//.test(location.hash) && pvis($('.anvil-role-pfx-crows')), 'cycle page after start', 40000);
    const cycleHash = location.hash;
    ok(/Flow cycle/.test(ptext('.pfx-cycle-page .anvil-role-page-title')), 'cycle: opens on the new cycle');
    ok($$('.anvil-role-pfx-crows .pfx-crow').length >= 3, 'cycle: everyone listed with self/manager status');
    ok($('.pfx-dist .hr-chart, .pfx-dist .hr-chart-empty'), 'cycle: rating chart drawn');
    ok($('.pfx-cycle-page [role=progressbar]').getAttribute('aria-valuenow') === '0', 'cycle: progress starts at 0');
    ok($$('.anvil-role-pfx-crows a.pfx-crow-link').some((a) => /^#review\//.test(a.getAttribute('href'))), 'cycle: links open each review');

    // ---- write my self-review: draft, then submit (asks first), then read-only
    await page('#performance/reviews', () => pvis($('.anvil-role-pfx-write-list')), 'reviews to write');
    const mineLink = $$('.anvil-role-pfx-write-list a').find((a) => /Flow cycle/.test(a.textContent) && /Self-review/.test(a.textContent));
    ok(mineLink, 'reviews: my self-review for the new cycle is listed with its due date');
    ok(/due /.test(mineLink.textContent), 'reviews: shows the due date');
    mineLink.click();
    await until(() => window.UI_READY && /^#review\//.test(location.hash) && $$(':is(.anvil-role-pfx-q-list textarea, textarea.anvil-role-pfx-q-list)').length >= 3, 'review page');
    const reviewHash = location.hash;
    $$(':is(.anvil-role-pfx-q-list textarea, textarea.anvil-role-pfx-q-list)').forEach((ta, i) => type(ta, 'Flow answer ' + (i + 1)));
    await click('.pfx-rating button', '3 Solid');
    await until(() => byText('.pfx-rating button', '3 Solid').getAttribute('aria-pressed') === 'true', 'rating pressed');
    ok(true, 'review: rating buttons say which one is chosen');
    await click('.pfx-review-actions button', 'Save draft');
    await until(() => /Draft saved/.test(document.body.textContent), 'draft saved toast');
    ok(true, 'review: Save draft');
    await click('.pfx-review-actions button', 'Submit review');
    await modalBtn('Submit review');
    await until(() => !pvis($(':is(.anvil-role-pfx-q-list textarea, textarea.anvil-role-pfx-q-list)')) && /Flow answer 1/.test(ptext('.anvil-role-pfx-q-list')) && /Submitted/.test(ptext('.pfx-review-head')), 'submitted read-only', 30000);
    ok(/3 of 5: Solid/.test(ptext('.pfx-rating-box')), 'review: read-only after submit, with the rating in words');

    // ---- cycle progress moved; close the cycle
    await page(cycleHash, () => pvis($('.anvil-role-pfx-crows')), 'cycle again');
    ok(Number($('.pfx-cycle-page [role=progressbar]').getAttribute('aria-valuenow')) > 0, 'cycle: progress counts the submitted review');
    await click('.pfx-cycle-page button', 'Close cycle');
    await modalBtn('Close cycle');
    await until(() => /Closed/.test(ptext('.pfx-cycle-page .ui-page-head')), 'cycle closed');
    ok(true, 'cycle: Close cycle asks, then closes');
    await page(reviewHash, () => pvis($('.anvil-role-pfx-q-list')), 'review after close');
    ok(!$(':is(.anvil-role-pfx-q-list textarea, textarea.anvil-role-pfx-q-list)') || !pvis($(':is(.anvil-role-pfx-q-list textarea, textarea.anvil-role-pfx-q-list)')), 'review: stays read-only once the cycle is closed');

    // ---- goals: add one, update it, delete it
    await page('#performance/goals', () => pvis($('.pfx-goals')), 'performance: goals');
    await click('.pfx-goals button', 'Add a goal');
    await until(() => $('.pfx-dlg-goal input'), 'goal dialog');
    type($('.pfx-dlg-goal input'), 'Flow goal ' + stamp);
    await click('.pfx-dlg-goal .pfx-quick button', '50%');
    ok($('.pfx-dlg-goal input[type=number]').value === '50', 'goal: quick progress buttons fill the number');
    await click('.pfx-dlg-goal button', 'Save goal');
    await until(() => !$('.pfx-dlg-goal') && /Flow goal/.test(ptext('.anvil-role-pfx-my-goals')), 'goal saved');
    const goalRow = $$('.anvil-role-pfx-my-goals .hr-goal').find((g) => /Flow goal/.test(g.textContent));
    ok(/50% done/.test(goalRow.textContent) && goalRow.querySelector('[role=progressbar]'), 'goals: new goal with a 50% progress bar');
    goalRow.querySelector('.anvil-role-ic-edit button').click();
    await until(() => $('.pfx-dlg-goal') && pvis(byText('.pfx-dlg-goal button', 'Delete goal')), 'goal dialog (edit)');
    await click('.pfx-dlg-goal button', 'Delete goal');
    await click('.pfx-dlg-goal button', 'Yes, delete it');
    await until(() => !$('.pfx-dlg-goal') && !/Flow goal/.test(ptext('.pfx-goals')), 'goal deleted');
    ok(true, 'goals: delete asks inside the dialog, then removes it');

    // ---- kudos
    await page('#performance/kudos', () => pvis($('.pfx-kudos')), 'performance: kudos');
    await click('.pfx-kudos button', 'Give kudos');
    await until(() => $('.pfx-dlg-kudos select') && $('.pfx-dlg-kudos select').options.length > 1, 'kudos dialog');
    pick($('.pfx-dlg-kudos select'), $('.pfx-dlg-kudos select').options[1].text);
    type($('.pfx-dlg-kudos textarea'), 'Flow kudos ' + stamp + ': thanks for the help');
    await click('.pfx-dlg-kudos button', 'Send kudos');
    await until(() => !$('.pfx-dlg-kudos') && /Flow kudos/.test(ptext('.anvil-role-pfx-kudos-feed')), 'kudos in the feed');
    ok($$('.anvil-role-pfx-kudos-feed .hr-kudos').length >= 1, 'kudos: sent and shown first in the feed');

    // ---- pulse: start a new one, answer it anonymously, see the 3-answer rule, close it
    await page('#performance/pulse', () => pvis($('.pfx-results')), 'performance: pulse (HR)');
    ok(/Pulse/.test($('.ui-tabs a.on').textContent), 'pulse: #performance/pulse opens the Pulse tab');
    await click('.pfx-results button', 'Start a new pulse');
    await modalBtn('Start the pulse');
    await until(() => window.UI_READY && pvis($('.pfx-answer')) && $$('.pfx-scale button').length === 11, 'pulse question shown', 30000);
    ok(/Anonymous/.test(ptext('.pfx-answer')) && /3 people/.test(ptext('.pfx-answer')), 'pulse: says it is anonymous and the 3-answer rule');
    await click('.pfx-scale button', '8');
    ok(byText('.pfx-scale button', '8').getAttribute('aria-pressed') === 'true', 'pulse: the chosen score is pressed');
    type($('.pfx-answer textarea'), 'Flow pulse comment');
    await click('.pfx-answer button', 'Send my answer');
    await until(() => pvis($('.pfx-thanks')) && !pvis($('.pfx-answer')), 'thank-you shown', 30000);
    ok(true, 'pulse: answer sent, thank-you shown');
    await until(() => $$('.anvil-role-pfx-surveys').some((e) => /Waiting for 3 answers \(\d so far\)/.test(e.textContent.replace(/\s+/g, ' '))),
      'hidden results line', 30000);
    ok(true, 'pulse: results hidden until 3 answers');
    const openCard = $$('.anvil-role-pfx-surveys .pfx-survey').find((c) => /Open/.test(c.textContent));
    openCard.querySelector('.anvil-role-ic-lock button').click();
    await modalBtn('Close the survey');
    await until(() => !$$('.anvil-role-pfx-surveys .pfx-survey').some((c) => /Open/.test(c.querySelector('.anvil-role-badge').textContent)), 'survey closed');
    ok(true, 'pulse: Close asks, then closes the survey');

    // ---- policies and news: post + delete an announcement
    await page('#docs', () => pvis($('.dc-anns')) && pvis($('.dc-policies')), 'docs');
    ok($$('.anvil-role-dc-policy-list .dc-prow').length >= 1, 'docs: policies listed');
    ok(/min read/.test(ptext('.anvil-role-dc-policy-list')) && /acknowledged/.test(ptext('.anvil-role-dc-policy-list')), 'docs: read time and HR acknowledgement counts');
    await click('.dc-anns button', 'Post an announcement');
    await until(() => $('.dc-dlg-ann input'), 'announce dialog');
    type($('.dc-dlg-ann input[type=text], .dc-dlg-ann input:not([type=checkbox])'), 'Flow news ' + stamp);
    type($('.dc-dlg-ann textarea'), 'Made by the UI test');
    $('.dc-dlg-ann input[type=checkbox]').click();
    await click('.dc-dlg-ann button', 'Post announcement');
    await until(() => !$('.dc-dlg-ann') && /Flow news/.test(ptext('.anvil-role-dc-ann-list')), 'announcement posted');
    const ann = $$('.anvil-role-dc-ann-list .hr-ann').find((a) => /Flow news/.test(a.textContent));
    ok(/Pinned/.test(ann.textContent), 'docs: announcement posted and pinned');
    ann.querySelector('.anvil-role-ic-trash button').click();
    await modalBtn('Delete');
    await until(() => !/Flow news/.test(ptext('.anvil-role-dc-ann-list')), 'announcement deleted');
    ok(true, 'docs: announcement deleted');

    // ---- new policy -> policy page -> acknowledge -> HR lists -> delete
    await click('.dc-policies button', 'New policy');
    await until(() => $('.dc-dlg-policy textarea'), 'policy dialog');
    type($('.dc-dlg-policy input:not([type=checkbox])'), 'Flow policy ' + stamp);
    type($('.dc-dlg-policy textarea'), 'First paragraph of the flow policy.\n\nSecond paragraph: be kind to each other.');
    await click('.dc-dlg-policy button', 'Save policy');
    await until(() => window.UI_READY && /^#policy\//.test(location.hash) && pvis($('.anvil-role-dc-body')), 'policy page', 30000);
    ok(/Second paragraph/.test(ptext('.anvil-role-dc-body')), 'policy: text shown');
    ok(getComputedStyle($('.anvil-role-dc-body')).whiteSpace === 'pre-line', 'policy: paragraphs kept (pre-line)');
    ok(/Not yet \(\d+\)/.test(ptext('.dc-who')), 'policy: HR sees who has not acknowledged');
    await click('.dc-ack button', 'I have read and understood this');
    await until(() => pvis($('.anvil-role-dc-acked')) && /You acknowledged this on/.test(ptext('.anvil-role-dc-acked')), 'acknowledged');
    ok(/Acknowledged \([1-9]/.test(ptext('.dc-who')), 'policy: acknowledgement recorded with the date, HR list updated');
    await click('.dc-policy-page button', 'Delete policy');
    await modalBtn('Delete policy');
    await until(() => window.UI_READY && location.hash === '#docs' && pvis($('.dc-policies')), 'back on docs');
    ok(!/Flow policy/.test(ptext('.anvil-role-dc-policy-list')), 'policy: deleted');

    // ---- reports: numbers, charts with takeaways, exports
    await page('#reports', () => pvis($('.rp-stats')) && $$('.rp-grid .hr-chart, .rp-grid .hr-chart-empty').length >= 9, 'reports');
    ok($$('.rp-stats .anvil-role-hr-big').every((b) => b.textContent.trim().length > 0), 'reports: stats strip filled');
    ok($$('.rp-grid .anvil-role-rp-take').length >= 9 && $$('.rp-grid .anvil-role-rp-take').every((t) => t.textContent.trim().length > 8), 'reports: every chart has a takeaway');
    ok(/biggest team/.test(ptext('.rp-grid')), 'reports: department takeaway names the biggest team');
    const got = [];
    const realDownload = window.HR.download;
    window.HR.download = (text, name) => { got.push({ text: text, name: name }); return true; };
    try {
      $('.rp-exports input[type=checkbox]').click();
      await click('.rp-exports button', 'Download people list');
      await until(() => got.length === 1, 'people csv');
      ok(/people\.csv$/.test(got[0].name) && /Pay rate/.test(got[0].text), 'reports: people CSV with pay downloads');
      ok(/^\d{4}-\d{2}-01$/.test($$('.rp-exports input[type=date]')[0].value), 'reports: payroll period starts on the 1st');
      await click('.rp-exports button', 'Download payroll export');
      await until(() => got.length === 2, 'payroll csv');
      ok(/payroll/.test(got[1].name) && /Paid days off/.test(got[1].text), 'reports: payroll export downloads');
    } finally {
      window.HR.download = realDownload;
    }
