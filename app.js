/**
 * 績效考核 Dashboard — app.js
 * Shared renderer for page1 (部門總覽), page2 (個人總覽), page3 (警示).
 * Fetches data.json and renders based on which page elements exist in DOM.
 */

const DATA_URL = 'data/data.json';

const TIER_ORDER = { S: 0, A: 1, B: 2, C: 3, D: 4 };
const ALERT_ORDER = { red: 0, orange: 1, amber: 2, ok: 3 };

// ── Helpers ──

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function sparkSvg(points, w, h) {
  if (!points || points.length < 2) return '';
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const pad = 2;
  const coords = points.map((v, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = pad + ((max - v) / range) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const last = points[points.length - 1];
  const first = points[0];
  const color = last > first ? '#3fb950' : last < first ? '#f85149' : '#6e7681';
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline fill="none" stroke="${color}" stroke-width="1.5" points="${coords}"/></svg>`;
}

function miniBarHtml(score) {
  const cls = score >= 70 ? '' : score >= 50 ? ' low' : ' bad';
  return `<span class="mini-bar${cls}"><i style="width:${Math.min(score, 100)}%"></i></span>`;
}

function statusClass(status) {
  return (status === '未達標' || status === '待改善') ? 'label-red' : 'label-green';
}

function initials(name) {
  if (!name) return '?';
  return name.length >= 2 ? name.slice(-2) : name;
}

// ── Data fetch ──

async function loadData() {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(res.status);
    return await res.json();
  } catch (e) {
    console.error('Failed to load data:', e);
    return null;
  }
}

// ── Generic slot renderer ──

function renderSlots(data) {
  document.querySelectorAll('[data-render]').forEach(el => {
    const path = el.dataset.render;
    const val = resolvePath(data, path);
    if (val !== undefined && val !== null) {
      el.textContent = val;
    }
  });
}

function resolvePath(obj, path) {
  return path.split('.').reduce((o, k) => o && o[k], obj);
}

// ══════════════════════════════════════════════
// PAGE 1 — 部門總覽
// ══════════════════════════════════════════════

function renderPage1(data) {
  const { stats, members, alert_summary } = data;

  // Stats
  renderSlots({
    stats,
    alerts_count: stats.alerts_count,
    member_count: stats.member_count,
    dept_subtitle: `${stats.department_name} · ${stats.member_count} members · ${stats.period_label}`,
  });

  // State
  let sortKey = 'score';
  let sortAsc = false;
  let filterTier = 'all';
  let filterAlert = 'all';
  let searchQuery = '';

  function sortMembers(arr) {
    const copy = [...arr];
    copy.sort((a, b) => {
      let va, vb;
      switch (sortKey) {
        case 'name': va = a.name; vb = b.name; return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        case 'tier': va = TIER_ORDER[a.tier] ?? 5; vb = TIER_ORDER[b.tier] ?? 5; break;
        case 'issues': va = a.issues; vb = b.issues; break;
        case 'score': va = a.current_score; vb = b.current_score; break;
        case 'trend': va = trendDelta(a); vb = trendDelta(b); break;
        case 'completion': va = a.current_score; vb = b.current_score; break;
        case 'alert': va = ALERT_ORDER[a.alert] ?? 4; vb = ALERT_ORDER[b.alert] ?? 4; break;
        default: va = a.current_score; vb = b.current_score;
      }
      return sortAsc ? va - vb : vb - va;
    });
    return copy;
  }

  function trendDelta(m) {
    const t = m.trend?.overall;
    if (!t || t.length < 2) return 0;
    return t[t.length - 1] - t[0];
  }

  function filterMembers(arr) {
    return arr.filter(m => {
      if (filterTier !== 'all' && m.tier !== filterTier) return false;
      if (filterAlert !== 'all') {
        if (filterAlert === 'ok' && m.alert !== 'ok') return false;
        if (filterAlert !== 'ok' && m.alert !== filterAlert) return false;
      }
      if (searchQuery && !m.name.includes(searchQuery) && !(m.role || '').includes(searchQuery)) return false;
      return true;
    });
  }

  function renderTable() {
    const filtered = filterMembers(sortMembers(members));
    const tbody = document.getElementById('member-tbody');
    if (!tbody) return;

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">沒有符合的成員</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(m => {
      const encoded = encodeURIComponent(m.name);
      const spark = sparkSvg(m.trend?.overall || [], 80, 18);
      const bar = miniBarHtml(m.current_score);
      return `<tr data-name="${esc(m.name)}" onclick="location.href='page2.html?name=${encoded}'">
        <td><span class="alert-dot ${m.alert || 'ok'}"></span></td>
        <td class="name-cell">
          <span class="avatar">${esc(m.initials || initials(m.name))}</span>
          <div>
            <div><a href="page2.html?name=${encoded}" class="link">${esc(m.name)}</a></div>
            <div class="role">${esc(m.role || '')}</div>
          </div>
        </td>
        <td><span class="tier tier-${m.tier}">${m.tier}</span></td>
        <td class="num">${m.issues}</td>
        <td class="num" style="font-size:14px;font-weight:500">${m.current_score}</td>
        <td>${spark}</td>
        <td>${bar}</td>
      </tr>`;
    }).join('');
  }

  // Sort headers
  document.querySelectorAll('th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (sortKey === key) { sortAsc = !sortAsc; } else { sortKey = key; sortAsc = false; }
      document.querySelectorAll('th[data-sort]').forEach(h => h.classList.remove('sorted', 'asc'));
      th.classList.add('sorted');
      if (sortAsc) th.classList.add('asc');
      renderTable();
    });
  });

  // Filter pills
  document.querySelectorAll('.filter-pill[data-filter]').forEach(pill => {
    pill.addEventListener('click', () => {
      const group = pill.dataset.filter;
      const val = pill.dataset.val;
      document.querySelectorAll(`.filter-pill[data-filter="${group}"]`).forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      if (group === 'tier') filterTier = val;
      if (group === 'alert') filterAlert = val;
      renderTable();
    });
  });

  // Search
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      searchQuery = searchInput.value.trim();
      renderTable();
    });
  }

  renderTable();
}

// ══════════════════════════════════════════════
// PAGE 2 — 個人總覽
// ══════════════════════════════════════════════

function renderPage2(data) {
  const params = new URLSearchParams(location.search);
  const name = params.get('name');
  if (!name) { location.href = 'page1.html'; return; }

  const member = data.members.find(m => m.name === name);
  if (!member) {
    document.querySelector('.page').innerHTML = `<div class="empty">找不到成員：${esc(name)}</div>`;
    return;
  }

  // Sidebar alerts count
  renderSlots({ alerts_count: data.stats.alerts_count });

  // Breadcrumb + header
  document.querySelectorAll('[data-render="member.name"]').forEach(el => el.textContent = member.name);
  const subtitleEl = document.querySelector('[data-render="member.subtitle"]');
  if (subtitleEl) subtitleEl.textContent = member.subtitle || `${member.role} · ${member.team || ''}`;

  // Profile head
  const avatarEl = document.querySelector('[data-render="member.initials"]');
  if (avatarEl) avatarEl.textContent = member.initials || initials(member.name);

  const metaEls = document.querySelectorAll('.profile-head .meta span');
  if (metaEls[0]) metaEls[0].textContent = member.role || '';
  if (metaEls[1]) metaEls[1].textContent = member.team || '';

  // Focus tags
  const tagRow = document.querySelector('.tag-row');
  if (tagRow && member.focus_tags) {
    tagRow.innerHTML = member.focus_tags.map(t => `<span class="label label-red">${esc(t)}</span>`).join('');
  }

  // Tier + score
  const tierEl = document.querySelector('[data-render-tier="member.tier"]');
  if (tierEl) {
    tierEl.textContent = member.tier;
    tierEl.className = `tier tier-lg tier-${member.tier}`;
  }
  const scoreEl = document.querySelector('[data-render="member.current_score"]');
  if (scoreEl) scoreEl.textContent = member.current_score;

  // Trend chart
  renderTrendChart(member);

  // Issues
  const issueCountEl = document.querySelector('[data-render="member.issue_count"]');
  if (issueCountEl) issueCountEl.textContent = (member.issue_list || []).length;

  const issuesSlot = document.getElementById('issues-slot');
  if (issuesSlot && member.issue_list) {
    issuesSlot.innerHTML = member.issue_list.map(iss => {
      const idHtml = iss.url
        ? `<a class="num issue-link" href="${esc(iss.url)}" target="_blank" rel="noopener">${esc(iss.id)}</a>`
        : `<div class="num">${esc(iss.id)}</div>`;
      const titleHtml = iss.url
        ? `<a class="title issue-link" href="${esc(iss.url)}" target="_blank" rel="noopener">${esc(iss.title)}</a>`
        : `<div class="title">${esc(iss.title)}</div>`;
      return `
      <div class="issue-row">
        ${idHtml}
        ${titleHtml}
        <div class="labels">
          <span class="label label-red">${esc(iss.category)}</span>
          <span class="label ${statusClass(iss.status)}">${esc(iss.status)}</span>
        </div>
      </div>
    `;
    }).join('');
  }

  // KPI grid
  const kpiGrid = document.querySelector('.kpi-grid');
  if (kpiGrid && member.kpis) {
    kpiGrid.innerHTML = member.kpis.map(kpi => {
      const delta = kpi.delta;
      const sign = delta >= 0 ? '+' : '';
      const spark = sparkSvg(kpi.trend, 60, 16);
      return `<div class="kpi-item">
        <div class="row1">
          <span class="label label-red">${esc(kpi.name)}</span>
          <span class="label ${statusClass(kpi.status)}">${esc(kpi.status)}</span>
        </div>
        <div class="score-big">${kpi.score}</div>
        <div class="trend-line">
          ${spark}
          <span>${kpi.prev} → ${kpi.score} (${sign}${delta})</span>
        </div>
      </div>`;
    }).join('');
  }
}

function renderTrendChart(member) {
  const slot = document.getElementById('chart-slot');
  const legendSlot = document.querySelector('.chart-legend');
  if (!slot || !member.trend) return;

  const { months, categories, series } = member.trend;
  if (!months || !categories || !series) return;

  const W = 500, H = 200, PAD = 40, PAD_B = 30, PAD_R = 20;
  const plotW = W - PAD - PAD_R;
  const plotH = H - PAD_B - 10;

  // Find global min/max
  let allVals = [];
  categories.forEach(c => {
    const s = series[c.name];
    if (s) allVals.push(...s);
  });
  const minV = Math.floor(Math.min(...allVals) / 5) * 5 - 5;
  const maxV = Math.ceil(Math.max(...allVals) / 5) * 5 + 5;
  const range = maxV - minV || 1;

  function x(i) { return PAD + (i / (months.length - 1)) * plotW; }
  function y(v) { return 10 + ((maxV - v) / range) * plotH; }

  // Grid lines
  let gridLines = '';
  for (let v = minV; v <= maxV; v += 10) {
    const yy = y(v);
    gridLines += `<line x1="${PAD}" x2="${W - PAD_R}" y1="${yy}" y2="${yy}" stroke="#21262d" stroke-width="1"/>`;
    gridLines += `<text x="${PAD - 6}" y="${yy + 4}" text-anchor="end" fill="#6e7681" font-size="10" font-family="JetBrains Mono, monospace">${v}</text>`;
  }

  // X axis labels
  let xLabels = months.map((m, i) =>
    `<text x="${x(i)}" y="${H - 5}" text-anchor="middle" fill="#6e7681" font-size="10" font-family="JetBrains Mono, monospace">${m}</text>`
  ).join('');

  // Lines
  let lines = categories.map(c => {
    const s = series[c.name];
    if (!s) return '';
    const pts = s.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    return `<polyline fill="none" stroke="${c.color}" stroke-width="2" points="${pts}"/>`;
  }).join('');

  slot.innerHTML = `<svg width="100%" viewBox="0 0 ${W} ${H}" style="max-width:${W}px">${gridLines}${xLabels}${lines}</svg>`;

  // Legend
  if (legendSlot) {
    legendSlot.innerHTML = categories.map(c =>
      `<span><i style="background:${c.color}"></i>${c.name}</span>`
    ).join('');
  }
}

// ══════════════════════════════════════════════
// PAGE 3 — 警示
// ══════════════════════════════════════════════

function renderPage3(data) {
  const { alerts, alert_summary, stats } = data;

  // Sidebar + banner
  renderSlots({
    alerts_count: stats.alerts_count,
    'alert_summary.red': alert_summary.red,
    'alert_summary.orange': alert_summary.orange,
    'alert_summary.amber': alert_summary.amber,
  });

  let filterLevel = 'all';
  let searchQuery = '';

  function filteredAlerts() {
    return alerts.filter(a => {
      if (filterLevel !== 'all' && a.level !== filterLevel) return false;
      if (searchQuery && !a.name.includes(searchQuery)) return false;
      return true;
    });
  }

  function renderAlertList() {
    const list = document.getElementById('alert-list');
    if (!list) return;
    const items = filteredAlerts();

    if (items.length === 0) {
      list.innerHTML = '<div class="empty">沒有警示</div>';
      return;
    }

    list.innerHTML = items.map(a => {
      const encoded = encodeURIComponent(a.name);
      return `<a class="alert-item" href="page2.html?name=${encoded}">
        <div class="stripe ${a.level}"></div>
        <span class="avatar">${esc(a.initials || initials(a.name))}</span>
        <div>
          <div class="name">${esc(a.name)} <span class="tier tier-${a.tier}" style="margin-left:6px">${a.tier}</span></div>
          <div class="reason">${esc(a.reason)}<span class="detail">· ${esc(a.detail || '')}</span></div>
        </div>
        <div class="date">${esc(a.date || '')}</div>
        <div class="action">›</div>
      </a>`;
    }).join('');
  }

  // Filter pills
  document.querySelectorAll('.filter-pill[data-alertfilter]').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill[data-alertfilter]').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      filterLevel = pill.dataset.alertfilter;
      renderAlertList();
    });
  });

  // Search
  const searchInput = document.getElementById('alert-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      searchQuery = searchInput.value.trim();
      renderAlertList();
    });
  }

  renderAlertList();
}

// ══════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
  const data = await loadData();
  if (!data) {
    document.querySelector('.main .page').innerHTML = '<div class="empty">無法載入資料</div>';
    return;
  }

  // Detect which page
  if (document.getElementById('member-table')) {
    renderPage1(data);
  } else if (document.querySelector('.profile-head')) {
    renderPage2(data);
  } else if (document.getElementById('alert-list')) {
    renderPage3(data);
  }
});
