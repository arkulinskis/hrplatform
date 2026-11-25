    // ================================================================ time off (Pages/TimeOff) + settings (Pages/Settings)
    const vis = (el) => !!(el && el.offsetParent);
    const isoDay = (d) => d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);

    // ---- time off: Mine
    await page('#timeoff', () => vis($('.to-balances')) && $$('.to-balances .hr-bal').length > 0, 'time off');
    ok($$('.to-balances .hr-bal').length >= 3, 'time off: balances shown');
    ok(vis($('.anvil-role-to-request button')), 'time off: Request time off button');

    // ---- request time off through the dialog (a Monday + Tuesday about three months out)
    const mineBefore = $$('.anvil-role-to-mine .to-row').length;
    const startDay = new Date(); startDay.setDate(startDay.getDate() + 95);
    while (startDay.getDay() !== 1) startDay.setDate(startDay.getDate() + 1);
    const endDay = new Date(startDay); endDay.setDate(endDay.getDate() + 1);
    await click('.anvil-role-to-request button');
    await until(() => $('.to-req :is(.anvil-role-to-req-type select, select.anvil-role-to-req-type)'), 'request dialog');
    ok(/left|limit|a year/.test($('.to-req :is(.anvil-role-to-req-type select, select.anvil-role-to-req-type)').options[0].text), 'request: types show what is left');
    pick($('.to-req :is(.anvil-role-to-req-type select, select.anvil-role-to-req-type)'), 'Vacation');
    type($('.to-req :is(.anvil-role-to-req-start input, input.anvil-role-to-req-start)'), isoDay(startDay));
    type($('.to-req :is(.anvil-role-to-req-end input, input.anvil-role-to-req-end)'), isoDay(endDay));
    await until(() => /2 days/.test($('.to-req .anvil-role-to-req-count').textContent), 'live working-day count');
    ok(true, 'request: live count of working days');
    type($('.to-req textarea'), 'Flow test trip');
    await click('.to-req .anvil-role-to-req-send button');
    await until(() => !$('.to-req') && $$('.anvil-role-to-mine .to-row').length === mineBefore + 1, 'request saved', 30000);
    const newRow = $('.anvil-role-to-mine .to-row');
    ok(/Waiting/.test(newRow.textContent) && /Flow test trip/.test(newRow.textContent), 'request: shows first in my list as Waiting');

    // ---- cancel it
    newRow.querySelector('.anvil-role-to-cancel button').click();
    await click('.anvil-modal-content button', 'Cancel request');
    await until(() => /Cancelled/.test(($('.anvil-role-to-mine .to-row') || {}).textContent || ''), 'request cancelled', 30000);
    ok(true, 'request: Cancel asks, then marks it Cancelled');

    // ---- calendar: month grid, next/previous month, chip highlights the request
    await page('#timeoff/calendar', () => vis($('.to-cal')) && $('.hr-cal'), 'calendar');
    const month0 = $('.anvil-role-to-month').textContent.trim();
    ok(month0.length > 3 && $$('.hr-cal-day').length >= 28, 'calendar: month grid for ' + month0);
    await click('.anvil-role-to-next button');
    await until(() => $('.anvil-role-to-month').textContent.trim() !== month0, 'next month');
    ok(vis($('.anvil-role-to-this-month button')), 'calendar: next month + This month button');
    await click('.anvil-role-to-this-month button');
    await until(() => $('.anvil-role-to-month').textContent.trim() === month0, 'back to this month');
    ok(true, 'calendar: back to this month');
    const chip = $('.hr-cal-chip');
    if (chip) {
      chip.click();
      await until(() => $('.anvil-role-to-out .to-row.to-hl'), 'chip highlights the request');
      ok(true, 'calendar: selecting a name highlights the request below');
    } else {
      ok(true, 'calendar: nobody out this month (no chip to select)');
    }

    // ---- approvals: approve one, decline one with a note
    await page('#timeoff/approvals', () => vis($('.to-appr-box')), 'approvals');
    const pend = $$('.anvil-role-to-appr .to-row').length;
    ok(pend >= 2, 'approvals: ' + pend + ' requests waiting (HR sees everyone)');
    ok(/Approvals\s*\d+/.test($$('.to-tabs a').find((a) => /Approvals/.test(a.textContent)).textContent), 'approvals: count on the tab');
    $('.anvil-role-to-appr .to-row .anvil-role-to-approve button').click();
    await until(() => $$('.anvil-role-to-appr .to-row').length === pend - 1, 'approved', 30000);
    ok(true, 'approvals: Approve removes it from the list');
    $('.anvil-role-to-appr .to-row .anvil-role-to-decline button').click();
    await until(() => $('.to-decide textarea'), 'decline dialog');
    type($('.to-decide textarea'), 'Short-staffed that week, sorry');
    await click('.to-decide .anvil-role-to-decide-go button');
    await until(() => !$('.to-decide') && $$('.anvil-role-to-appr .to-row').length === pend - 2, 'declined', 30000);
    ok(true, 'approvals: Decline asks for a note, then removes it');

    // ---- holidays: add one, then delete it
    await page('#timeoff/holidays', () => vis($('.to-hol-add')), 'holidays');
    const holBefore = $$('.anvil-role-to-hol-list .to-hol').length;
    ok(holBefore >= 1, 'holidays: company holidays listed');
    const holDay = new Date(); holDay.setDate(holDay.getDate() + 200 + Math.floor(Math.random() * 60));
    type($('.to-hol-add .to-hol-name input'), 'Flow Test Day');
    type($('.to-hol-add input[type=date]'), isoDay(holDay));
    await click('.anvil-role-to-hol-add-btn button');
    await until(() => $$('.anvil-role-to-hol-list .to-hol').some((h) => /Flow Test Day/.test(h.textContent)), 'holiday added', 30000);
    ok(true, 'holidays: HR adds a holiday');
    $$('.anvil-role-to-hol-list .to-hol').find((h) => /Flow Test Day/.test(h.textContent)).querySelector('.anvil-role-to-hol-del button').click();
    await click('.anvil-modal-content button', 'Delete');
    await until(() => !$$('.anvil-role-to-hol-list .to-hol').some((h) => /Flow Test Day/.test(h.textContent)), 'holiday deleted', 30000);
    ok(true, 'holidays: delete asks, then removes it');

    // ---- settings: company + department chips
    await page('#settings', () => vis($('.st-company')) && $(':is(.anvil-role-st-name input, input.anvil-role-st-name)').value, 'settings');
    ok($$('.st-list-departments .st-chip').length >= 1, 'settings: departments as chips');
    await click('.anvil-role-st-save-company button');
    await sleep(800);
    ok(vis($('.st-company')), 'settings: Save company');
    type($('.st-list-departments .st-add input'), 'Flow Dept');
    await click('.st-list-departments .anvil-role-st-add-btn button');
    await until(() => $$('.st-list-departments .st-chip').some((c) => /Flow Dept/.test(c.textContent)), 'department added', 30000);
    ok(true, 'settings: department added');
    $$('.st-list-departments .st-chip').find((c) => /Flow Dept/.test(c.textContent)).querySelector('.anvil-role-st-chip-x button').click();
    await until(() => !$$('.st-list-departments .st-chip').some((c) => /Flow Dept/.test(c.textContent)), 'department removed', 30000);
    ok(true, 'settings: department removed with its x');

    // ---- settings: leave types (add, then delete)
    await page('#settings/timeoff', () => $$('.anvil-role-st-types .st-type').length >= 2, 'settings time off');
    await click('.anvil-role-st-add-type button');
    const newType = await until(() => $('.st-type.new'), 'new type row');
    type(newType.querySelector('.st-type-name input'), 'Flow Leave');
    type(newType.querySelector('.st-type-days input'), '3');
    newType.querySelector('.anvil-role-st-type-save button').click();
    await until(() => !$('.st-type.new') && $$('.st-type-name input').some((i) => i.value === 'Flow Leave'), 'type added', 30000);
    ok(true, 'settings: leave type added');
    $$('.anvil-role-st-types .st-type').find((r) => r.querySelector('.st-type-name input').value === 'Flow Leave').querySelector('.anvil-role-st-type-del button').click();
    await click('.anvil-modal-content button', 'Delete');
    await until(() => !$$('.st-type-name input').some((i) => i.value === 'Flow Leave'), 'type deleted', 30000);
    ok(true, 'settings: unused leave type deleted');

    // ---- settings: checklist templates (add a task, save, reload, remove it again)
    await page('#settings/checklists', () => $$('.st-cl-onboarding .st-task').length >= 1, 'checklists');
    const tasks0 = $$('.st-cl-onboarding .st-task').length;
    await click('.st-cl-onboarding .anvil-role-st-task-add button');
    await until(() => $$('.st-cl-onboarding .st-task').length === tasks0 + 1, 'task row added');
    type($$('.st-cl-onboarding .st-task-title input').pop(), 'Flow test task');
    type($$('.st-cl-onboarding .st-task-day input').pop(), '3');
    await click('.st-cl-onboarding .anvil-role-st-task-save button');
    await sleep(1200);
    await page('#settings/company', () => vis($('.st-company')));
    await page('#settings/checklists', () => $$('.st-cl-onboarding .st-task').length >= 1, 'checklists again');
    ok($$('.st-cl-onboarding .st-task-title input').some((i) => i.value === 'Flow test task'), 'checklists: new task saved');
    const rows = $$('.st-cl-onboarding .st-task');
    rows.find((r) => r.querySelector('.st-task-title input').value === 'Flow test task').querySelector('.anvil-role-st-task-del button').click();
    await until(() => $$('.st-cl-onboarding .st-task').length === tasks0, 'task row removed');
    await click('.st-cl-onboarding .anvil-role-st-task-save button');
    await sleep(1200);
    ok(true, 'checklists: task removed and saved');

    // ---- settings: people data (import preview + import one person; sample + export shown)
    await page('#settings/data', () => vis($('.st-data-import')), 'people data');
    ok(vis($('.anvil-role-st-export button')), 'people data: Export everything');
    ok(vis($('.anvil-role-st-remove-sample button')), 'people data: Remove sample data (the company has sample data)');
    await click('.anvil-role-st-import button');
    await until(() => $('.st-import textarea'), 'import dialog');
    const mail = 'flow.import.' + Date.now() + '@example.com';
    type($('.st-import textarea'), 'First name,Last name,Email,Title\nIma,Porter,' + mail + ',Analyst\n,Nobody,bad-email,Ghost');
    await click('.anvil-role-st-import-preview button');
    await until(() => $$('.st-import .st-imp').length === 2, 'preview rows');
    ok($$('.st-import .st-imp.bad').length === 1, 'import: the row with problems is highlighted');
    ok(/Import 1 person/.test($('.anvil-role-st-import-go button').textContent), 'import: Import 1 person');
    await click('.anvil-role-st-import-go button');
    await until(() => !$('.st-import'), 'imported', 30000);
    ok(true, 'import: one person added, the bad row skipped');

    // ---- settings: audit log with a filter
    await page('#settings/audit', () => $$('.anvil-role-st-audit .hr-hist').length > 0, 'audit log');
    const auditAll = $$('.anvil-role-st-audit .hr-hist').length;
    ok(auditAll > 3, 'audit log: ' + auditAll + ' changes');
    type($(':is(.anvil-role-st-filter input, input.anvil-role-st-filter)'), 'zzzz-nothing');
    await until(() => $$('.anvil-role-st-audit .hr-hist').length === 0, 'filter narrows');
    ok(/0 changes/.test($('.anvil-role-st-audit-count').textContent), 'audit log: filter with no match');
    type($(':is(.anvil-role-st-filter input, input.anvil-role-st-filter)'), '');
    await until(() => $$('.anvil-role-st-audit .hr-hist').length === auditAll, 'filter cleared');
    ok(true, 'audit log: clearing the filter shows everything again');
