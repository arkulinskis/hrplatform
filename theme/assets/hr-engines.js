/* hr-engines.js: the drawing engines Python is too slow for. Wrapped by client_code/engines.py and the
   Components (OrgChart, Chart, MonthCalendar). Every name and title goes in with textContent (never innerHTML).

   HR.orgChart(el, json, opts)   tidy tree of people (+ dashed open roles); opts: {animate, onSelect(id), focus}
   HR.chart(el, kind, json, opts) "bar" | "hbar" | "line"; data = [{label, value}], opts: {unit, max}
   HR.calendar(el, month, json, holidaysJson, today, onPick)   month grid of who's out
*/
(function () {
  var HR = window.HR = window.HR || {};
  var NS = 'http://www.w3.org/2000/svg';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function svg(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function el(tag, cls, parent, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  }
  function parse(j) { return typeof j === 'string' ? JSON.parse(j || 'null') : j; }
  function clip(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; }

  /* ---------------------------------------------------------------- org chart (tidy tree) */
  HR.orgChart = function (host, json, opts) {
    opts = opts || {};
    var data = parse(json) || {nodes: [], open_roles: []};
    host.textContent = '';
    var byId = {}, roots = [];
    data.nodes.forEach(function (n) { n.kids = []; byId[n.id] = n; });
    data.nodes.forEach(function (n) {
      if (n.manager_id && byId[n.manager_id]) byId[n.manager_id].kids.push(n); else roots.push(n);
    });
    (data.open_roles || []).forEach(function (r, i) {
      var o = {id: 'open-' + i, name: 'Open role', title: r.title, department: r.department, open: true, kids: []};
      if (r.manager_id && byId[r.manager_id]) byId[r.manager_id].kids.push(o); else roots.push(o);
    });
    function sortKids(n) {
      n.kids.sort(function (a, b) { return (a.open ? 1 : 0) - (b.open ? 1 : 0) || (b.kids.length - a.kids.length) || String(a.name).localeCompare(b.name); });
      n.kids.forEach(sortKids);
    }
    roots.forEach(sortKids);
    var W = 176, H = 64, GX = 18, GY = 46;
    /* leaves of big teams stack vertically (keeps wide companies readable) */
    function layout(n, depth) {
      n.depth = depth;
      var leafs = n.kids.length > 3 && n.kids.every(function (k) { return !k.kids.length; });
      n.stack = leafs;
      if (!n.kids.length) { n.w = W; n.h = H; return; }
      n.kids.forEach(function (k) { layout(k, depth + 1); });
      if (leafs) { n.w = W + 28; n.h = H + GY + n.kids.length * (H + 12); return; }
      n.w = Math.max(W, n.kids.reduce(function (s, k) { return s + k.w; }, 0) + GX * (n.kids.length - 1));
      n.h = H + GY + Math.max.apply(null, n.kids.map(function (k) { return k.h; }));
    }
    function place(n, x, y) {
      n.x = x + n.w / 2 - W / 2; n.y = y;
      if (n.stack) {
        n.kids.forEach(function (k, i) { k.x = n.x + 28; k.y = y + H + GY + i * (H + 12); });
        return;
      }
      var cx = x;
      n.kids.forEach(function (k) { place(k, cx, y + H + GY); cx += k.w + GX; });
    }
    var totalW = 0, maxH = 0, x0 = 0;
    roots.forEach(function (r) { layout(r, 0); totalW += r.w + GX * 2; maxH = Math.max(maxH, r.h); });
    roots.forEach(function (r) { place(r, x0, 0); x0 += r.w + GX * 2; });
    var pad = 16, vw = Math.max(totalW, W) + pad * 2, vh = maxH + pad * 2;
    var s = svg('svg', {viewBox: (-pad) + ' ' + (-pad) + ' ' + vw + ' ' + vh, width: vw, height: vh, role: opts.onSelect ? 'group' : 'img',
                        'aria-label': 'Org chart of ' + (data.company || 'the company') + ', ' + data.nodes.length + ' people',
                        'class': 'hr-org' + (opts.animate && !reduce ? ' hr-org-anim' : '')}, host);
    var links = svg('g', {'class': 'hr-org-links'}, s), cards = svg('g', {}, s);
    var all = [];
    (function walk(list) { list.forEach(function (n) { all.push(n); walk(n.kids); }); })(roots);
    all.forEach(function (n) {
      n.kids.forEach(function (k) {
        var d;
        if (n.stack) {
          var lx = n.x + 14;
          d = 'M' + lx + ' ' + (n.y + H) + ' V' + (k.y + H / 2) + ' H' + k.x;
        } else {
          var x1 = n.x + W / 2, y1 = n.y + H, x2 = k.x + W / 2, y2 = k.y, my = y1 + GY / 2;
          d = 'M' + x1 + ' ' + y1 + ' V' + my + ' H' + x2 + ' V' + y2;
        }
        var p = svg('path', {d: d, 'class': 'hr-org-link' + (k.open ? ' open' : '')}, links);
        p.style.setProperty('--d', (k.depth * 0.32) + 's');
      });
    });
    all.forEach(function (n) {
      var g = svg('g', {'class': 'hr-org-node' + (n.open ? ' open' : '') + (n.me ? ' me' : '') + (n.id === opts.focus ? ' focus' : ''),
                        transform: 'translate(' + n.x + ',' + n.y + ')', tabindex: n.open || !opts.onSelect ? null : 0,
                        role: n.open || !opts.onSelect ? null : 'button', 'data-id': n.id,
                        'aria-label': !opts.onSelect ? null : (n.open ? 'Open role: ' + n.title : n.name + ', ' + (n.title || ''))}, cards);
      g.style.setProperty('--d', (n.depth * 0.32 + 0.12) + 's');
      svg('rect', {width: W, height: H, rx: 10, 'class': 'hr-org-card'}, g);
      if (!n.open) {
        svg('circle', {cx: 30, cy: H / 2, r: 18, 'class': 'hr-org-av tone-' + (n.tone || 0)}, g);
        svg('text', {x: 30, y: H / 2 + 4.5, 'text-anchor': 'middle', 'class': 'hr-org-ini tone-' + (n.tone || 0)}, g).textContent = n.initials || '?';
      } else {
        svg('circle', {cx: 30, cy: H / 2, r: 18, 'class': 'hr-org-av open'}, g);
        svg('text', {x: 30, y: H / 2 + 5, 'text-anchor': 'middle', 'class': 'hr-org-ini open'}, g).textContent = '+';
      }
      svg('text', {x: 56, y: 27, 'class': 'hr-org-name'}, g).textContent = clip(n.name, 18);
      svg('text', {x: 56, y: 45, 'class': 'hr-org-title'}, g).textContent = clip(n.title, 22);
      if (n.status === 'onboarding' || n.status === 'leave') {
        svg('circle', {cx: W - 12, cy: 12, r: 4.5, 'class': 'hr-org-dot ' + n.status}, g);
      }
      if (!n.open && opts.onSelect) {
        var pick = function (e) {
          if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return;
          e.preventDefault(); opts.onSelect(n.id);
        };
        g.addEventListener('click', pick); g.addEventListener('keydown', pick);
      }
    });
    if (opts.focus && byId[opts.focus]) {
      var f = byId[opts.focus];
      setTimeout(function () { host.scrollLeft = Math.max(0, f.x + pad - host.clientWidth / 2 + W / 2); }, 30);
    } else if (roots.length) {
      setTimeout(function () { host.scrollLeft = Math.max(0, (vw - host.clientWidth) / 2); }, 30);
    }
    return {count: data.nodes.length};
  };

  /* ---------------------------------------------------------------- charts */
  HR.chart = function (host, kind, json, opts) {
    opts = opts || {};
    var data = parse(json) || [];
    host.textContent = '';
    if (!data.length) { el('p', 'hr-chart-empty', host, 'No data yet.'); return; }
    var width = Math.max(260, host.clientWidth || 520);
    var max = opts.max || Math.max.apply(null, data.map(function (d) { return Math.abs(d.value) || 0; })) || 1;
    var unit = opts.unit || '';
    var title = data.map(function (d) { return d.label + ': ' + d.value + unit; }).join(', ');
    if (kind === 'hbar') {
      var rowH = 30, labW = Math.min(150, width * 0.38), h = data.length * rowH + 6;
      var s = svg('svg', {viewBox: '0 0 ' + width + ' ' + h, width: '100%', height: h, role: 'img', 'aria-label': title, 'class': 'hr-chart'}, host);
      data.forEach(function (d, i) {
        var y = i * rowH + 4, bw = Math.max(2, (width - labW - 46) * (d.value / max));
        svg('text', {x: 0, y: y + 16, 'class': 'hr-chart-lab'}, s).textContent = clip(d.label, 20);
        svg('rect', {x: labW, y: y + 4, width: bw, height: 16, rx: 4, 'class': 'hr-chart-bar c' + (i % 6)}, s);
        svg('text', {x: labW + bw + 6, y: y + 16, 'class': 'hr-chart-val'}, s).textContent = d.value + unit;
      });
      return;
    }
    var H = opts.height || 180, top = 16, bottom = 26, left = 34, right = 8;
    var s2 = svg('svg', {viewBox: '0 0 ' + width + ' ' + H, width: '100%', height: H, role: 'img', 'aria-label': title, 'class': 'hr-chart'}, host);
    var ih = H - top - bottom, iw = width - left - right;
    var vals = data.map(function (d) { return +d.value || 0; });
    var lo = Math.min(0, Math.min.apply(null, vals)), hi = Math.max(0, Math.max.apply(null, vals));
    if (opts.max) hi = Math.max(hi, opts.max);
    if (hi === lo) hi = lo + 1;
    var y = function (v) { return top + ih - ih * ((v - lo) / (hi - lo)); };
    var ticks = lo < 0 ? [lo, 0, hi] : [0, Math.round(hi / 2), hi];
    ticks.forEach(function (t) {
      svg('line', {x1: left, x2: width - right, y1: y(t), y2: y(t), 'class': 'hr-chart-grid' + (t === 0 && lo < 0 ? ' zero' : '')}, s2);
      svg('text', {x: left - 6, y: y(t) + 4, 'text-anchor': 'end', 'class': 'hr-chart-axis'}, s2).textContent = t;
    });
    var step = iw / data.length;
    var every = Math.ceil(data.length / Math.max(1, Math.floor(iw / 44)));
    if (kind === 'line') {
      var pts = data.map(function (d, i) { return [left + step * i + step / 2, y(+d.value || 0)]; });
      var base = y(Math.max(lo, 0));
      var area = 'M' + pts[0][0] + ' ' + base + pts.map(function (p) { return ' L' + p[0] + ' ' + p[1]; }).join('') + ' L' + pts[pts.length - 1][0] + ' ' + base + 'Z';
      svg('path', {d: area, 'class': 'hr-chart-area'}, s2);
      svg('path', {d: 'M' + pts.map(function (p) { return p[0] + ' ' + p[1]; }).join(' L'), 'class': 'hr-chart-line'}, s2);
      pts.forEach(function (p, i) {
        svg('circle', {cx: p[0], cy: p[1], r: 3.5, 'class': 'hr-chart-pt'}, s2);
        if (i === pts.length - 1) svg('text', {x: p[0], y: p[1] - 9, 'text-anchor': 'end', 'class': 'hr-chart-val'}, s2).textContent = data[i].value + unit;
      });
    } else {
      data.forEach(function (d, i) {
        var v = +d.value || 0, bw = Math.min(34, step * 0.62), x = left + step * i + (step - bw) / 2;
        var y0 = y(0), y1 = y(v), bh = Math.max(v ? 2 : 0, Math.abs(y0 - y1));
        svg('rect', {x: x, y: v >= 0 ? y0 - bh : y0, width: bw, height: bh, rx: 4, 'class': 'hr-chart-bar c' + (opts.single ? 0 : i % 6)}, s2);
        if (v && data.length <= 14) svg('text', {x: x + bw / 2, y: v >= 0 ? y0 - bh - 5 : y0 + bh + 13, 'text-anchor': 'middle', 'class': 'hr-chart-val'}, s2).textContent = d.value + unit;
      });
    }
    data.forEach(function (d, i) {
      if (i % every) return;
      svg('text', {x: left + step * i + step / 2, y: H - 8, 'text-anchor': 'middle', 'class': 'hr-chart-axis'}, s2).textContent = clip(d.label, 9);
    });
  };

  /* ---------------------------------------------------------------- month calendar */
  var DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  function iso(d) { return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
  HR.calendar = function (host, month, json, holidaysJson, today, onPick) {
    var items = parse(json) || [], hol = {};
    (parse(holidaysJson) || []).forEach(function (h) { hol[h.date] = h.name; });
    host.textContent = '';
    var p = String(month).split('-'), first = new Date(+p[0], +p[1] - 1, 1);
    var start = new Date(first); start.setDate(1 - ((first.getDay() + 6) % 7));
    var grid = el('div', 'hr-cal', host);
    DOW.forEach(function (d) { el('div', 'hr-cal-dow', grid, d); });
    for (var i = 0; i < 42; i++) {
      var d = new Date(start); d.setDate(start.getDate() + i);
      if (i >= 35 && d.getMonth() !== first.getMonth()) break;
      var key = iso(d), cell = el('div', 'hr-cal-day', grid);
      if (d.getMonth() !== first.getMonth()) cell.classList.add('other');
      if (d.getDay() === 0 || d.getDay() === 6) cell.classList.add('weekend');
      if (key === today) cell.classList.add('today');
      el('span', 'hr-cal-num', cell, String(d.getDate()));
      if (hol[key]) { cell.classList.add('holiday'); el('span', 'hr-cal-hol', cell, clip(hol[key], 18)); }
      var here = items.filter(function (r) { return r.start <= key && key <= r.end && d.getDay() !== 0 && d.getDay() !== 6; });
      here.slice(0, 3).forEach(function (r) {
        var chip = el('button', 'hr-cal-chip lv-' + (r.color || 'slate') + (r.status === 'pending' ? ' pending' : ''), cell, clip(r.person.split(' ')[0], 11));
        chip.type = 'button';
        chip.title = r.person + ': ' + r.type + (r.status === 'pending' ? ' (waiting for approval)' : '');
        chip.setAttribute('aria-label', chip.title + ', ' + key);
        if (onPick) chip.addEventListener('click', function (rr) { return function () { onPick(rr.id); }; }(r));
      });
      if (here.length > 3) el('span', 'hr-cal-more', cell, '+' + (here.length - 3) + ' more');
    }
  };

  /* ---------------------------------------------------------------- small helpers */
  HR.download = function (text, name, mime) {
    var blob = new Blob([text], {type: mime || 'text/plain'}), a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 400);
    return true;
  };
  HR.copy = function (text) {
    function fallback() {  // no clipboard permission (unfocused page, old browser): copy through a hidden field
      var t = document.createElement('textarea'); t.value = text; t.setAttribute('readonly', '');
      t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select();
      try { document.execCommand('copy'); } catch (e) {}
      t.remove();
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).catch(fallback);
      else fallback();
      return true;
    } catch (e) { fallback(); return false; }
  };
})();
