/* ═══════════════════════════════════════════════════
   ALPHATEX — ADMIN JAVASCRIPT
   Omnibar, Sidebar collapse, Charts, Sort tables,
   Bulk actions, Toast notifications, Theme toggle,
   Modals, Session timer
   ═══════════════════════════════════════════════════ */

const $ = (s, ctx = document) => ctx.querySelector(s);
const $$ = (s, ctx = document) => [...ctx.querySelectorAll(s)];

// ─── Theme ─────────────────────────────────────────
const adminTheme = {
  load() {
    const saved = localStorage.getItem('admin-theme') || 'dark';
    document.documentElement.setAttribute('data-admin-theme', saved);
    this.updateBtn(saved);
  },
  toggle() {
    const cur = document.documentElement.getAttribute('data-admin-theme');
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-admin-theme', next);
    localStorage.setItem('admin-theme', next);
    this.updateBtn(next);
  },
  updateBtn(theme) {
    const btn = $('#theme-toggle-btn');
    if (btn) btn.innerHTML = theme === 'dark'
      ? '<i class="fa-solid fa-sun"></i>'
      : '<i class="fa-solid fa-moon"></i>';
  }
};

// ─── Sidebar collapse ──────────────────────────────
const sidebar = {
  init() {
    const collapsed = localStorage.getItem('admin-sidebar') === 'collapsed';
    if (collapsed) this.collapse(false);

    const btn = $('#sidebar-collapse-btn');
    if (btn) btn.addEventListener('click', () => this.toggle());
  },
  toggle() {
    const sb = $('.admin-sidebar');
    const wrap = $('.admin-content-wrap');
    if (!sb) return;
    if (sb.classList.contains('collapsed')) { this.expand(); } else { this.collapse(); }
  },
  collapse(save = true) {
    const sb = $('.admin-sidebar');
    const wrap = $('.admin-content-wrap');
    sb?.classList.add('collapsed');
    wrap?.classList.add('sidebar-collapsed');
    if (save) localStorage.setItem('admin-sidebar', 'collapsed');
  },
  expand(save = true) {
    const sb = $('.admin-sidebar');
    const wrap = $('.admin-content-wrap');
    sb?.classList.remove('collapsed');
    wrap?.classList.remove('sidebar-collapsed');
    if (save) localStorage.setItem('admin-sidebar', 'expanded');
  }
};

// ─── Omnibar (Ctrl+K / Cmd+K) ─────────────────────
const omnibar = {
  data: [], selectedIndex: -1,
  init() {
    document.addEventListener('keydown', e => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); this.open(); }
      if (e.key === 'Escape') this.close();
    });
    const overlay = $('#omnibar-overlay');
    if (overlay) overlay.addEventListener('click', e => { if (e.target === overlay) this.close(); });

    const input = $('#omnibar-input');
    if (input) {
      input.addEventListener('input', e => this.search(e.target.value));
      input.addEventListener('keydown', e => this.handleKey(e));
    }
    const trigger = $('#omnibar-trigger');
    if (trigger) trigger.addEventListener('click', () => this.open());
  },
  open() {
    const overlay = $('#omnibar-overlay');
    overlay?.classList.add('active');
    setTimeout(() => $('#omnibar-input')?.focus(), 50);
    this.search('');
  },
  close() {
    $('#omnibar-overlay')?.classList.remove('active');
    const input = $('#omnibar-input');
    if (input) input.value = '';
  },
  search(q) {
    const items = [
      { icon: 'fa-gauge', title: 'Dashboard', url: '/admin/' },
      { icon: 'fa-box-open', title: 'Orders', url: '/admin/orders' },
      { icon: 'fa-shirt', title: 'Products', url: '/admin/products' },
      { icon: 'fa-list', title: 'Categories', url: '/admin/categories' },
      { icon: 'fa-users', title: 'Customers', url: '/admin/users' },
      { icon: 'fa-tag', title: 'Coupons', url: '/admin/coupons' },
      { icon: 'fa-boxes-stacked', title: 'Inventory', url: '/admin/inventory' },
      { icon: 'fa-shield-halved', title: 'Security', url: '/admin/security' },
      { icon: 'fa-scroll', title: 'Audit Log', url: '/admin/audit-log' },
      { icon: 'fa-gear', title: 'Settings', url: '/admin/settings' },
      { icon: 'fa-user-shield', title: 'Admin Team', url: '/admin/team' },
      { icon: 'fa-images', title: 'Carousel', url: '/admin/carousel' },
      { icon: 'fa-clock-rotate-left', title: 'Login History', url: '/admin/login-history' },
    ];
    const q_low = q.toLowerCase().trim();
    const filtered = q_low ? items.filter(i => i.title.toLowerCase().includes(q_low)) : items;
    this.renderResults(filtered);
  },
  renderResults(items) {
    const box = $('#omnibar-results');
    if (!box) return;
    this.selectedIndex = -1;
    if (!items.length) {
      box.innerHTML = '<div class="omnibar-empty">No results found.</div>';
      return;
    }
    box.innerHTML = items.map((item, i) => `
      <a class="omnibar-result" href="${item.url}" data-idx="${i}">
        <i class="fa-solid ${item.icon}"></i>
        <div><div class="res-title">${item.title}</div></div>
      </a>`).join('');
  },
  handleKey(e) {
    const results = $$('.omnibar-result');
    if (e.key === 'ArrowDown') { e.preventDefault(); this.selectedIndex = Math.min(this.selectedIndex + 1, results.length - 1); this.highlightResult(results); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); this.selectedIndex = Math.max(this.selectedIndex - 1, 0); this.highlightResult(results); }
    else if (e.key === 'Enter') { const sel = results[this.selectedIndex]; if (sel) { window.location.href = sel.href; } }
  },
  highlightResult(results) {
    results.forEach((r, i) => r.classList.toggle('selected', i === this.selectedIndex));
    results[this.selectedIndex]?.scrollIntoView({ block: 'nearest' });
  }
};

// ─── Table Sort ─────────────────────────────────────
function initTableSort() {
  $$('.admin-table.sortable thead th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const table = th.closest('table');
      const col = th.dataset.col;
      const asc = th.dataset.dir !== 'asc';
      th.dataset.dir = asc ? 'asc' : 'desc';
      $$('th', table).forEach(h => h.classList.remove('sorted'));
      th.classList.add('sorted');
      th.querySelector('.sort-icon').textContent = asc ? ' ↑' : ' ↓';

      const tbody = table.querySelector('tbody');
      const rows = $$('tr', tbody);
      rows.sort((a, b) => {
        const va = a.cells[th.cellIndex]?.textContent.trim() || '';
        const vb = b.cells[th.cellIndex]?.textContent.trim() || '';
        return asc ? va.localeCompare(vb, undefined, { numeric: true }) : vb.localeCompare(va, undefined, { numeric: true });
      });
      rows.forEach(r => tbody.appendChild(r));
    });
  });
}

// ─── Table Search Filter ─────────────────────────────
function initTableSearch() {
  $$('.table-search[data-target]').forEach(input => {
    input.addEventListener('input', () => {
      const table = $(input.dataset.target);
      if (!table) return;
      const q = input.value.toLowerCase();
      $$('tbody tr', table).forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  });
}

// ─── Bulk Selection ─────────────────────────────────
function initBulkSelect() {
  $$('[data-bulk-group]').forEach(container => {
    const selectAll = $('[data-select-all]', container) || $('[data-select-all]');
    const checkboxes = $$('input[type="checkbox"][data-bulk]');
    const bulkBar = $('.bulk-bar');
    const countSpan = $('#bulk-count');

    const updateBar = () => {
      const checked = checkboxes.filter(c => c.checked);
      if (bulkBar) bulkBar.classList.toggle('visible', checked.length > 0);
      if (countSpan) countSpan.textContent = checked.length;
    };

    selectAll?.addEventListener('change', () => {
      checkboxes.forEach(c => c.checked = selectAll.checked);
      updateBar();
    });
    checkboxes.forEach(c => c.addEventListener('change', updateBar));
  });
}

// ─── Bulk Action Form Submit ─────────────────────────
function bulkAction(action) {
  const ids = $$('input[data-bulk]:checked').map(c => c.value);
  if (!ids.length) { showToast('Select at least one item.', 'error'); return; }
  if (!confirm(`Apply "${action}" to ${ids.length} items?`)) return;
  const form = document.createElement('form');
  form.method = 'POST'; form.action = `/admin/bulk/${action}`;
  const csrf = document.querySelector('[name=csrf_token]');
  if (csrf) { const h = document.createElement('input'); h.type='hidden'; h.name='csrf_token'; h.value=csrf.value; form.appendChild(h); }
  ids.forEach(id => { const h = document.createElement('input'); h.type='hidden'; h.name='ids[]'; h.value=id; form.appendChild(h); });
  document.body.appendChild(form); form.submit();
}

// ─── Modals ─────────────────────────────────────────
function openModal(id) { $(`#${id}`)?.classList.add('active'); }
function closeModal(id) { $(`#${id}`)?.classList.remove('active'); }
$$('.modal-overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.remove('active'); });
});

// ─── Toast ─────────────────────────────────────────
function showToast(msg, type = 'success') {
  let container = $('.toast-container');
  if (!container) { container = document.createElement('div'); container.className = 'toast-container'; document.body.appendChild(container); }
  const icon = type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-circle-xmark' : 'fa-info-circle';
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateY(8px)'; toast.style.transition = '.3s'; setTimeout(() => toast.remove(), 350); }, 3000);
}

// ─── Session timer ─────────────────────────────────
function initSessionTimer() {
  const display = $('#timer-display');
  if (!display) return;
  let secs = 1800;
  const tick = () => {
    secs--;
    if (secs <= 0) { window.location.href = '/admin/logout'; return; }
    const m = String(Math.floor(secs / 60)).padStart(2, '0');
    const s = String(secs % 60).padStart(2, '0');
    display.textContent = `${m}:${s}`;
    if (secs < 300) display.style.color = 'var(--a-danger)';
  };
  setInterval(tick, 1000);
}

// ─── Settings tabs ──────────────────────────────────
function initSettingsTabs() {
  $$('.settings-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      $$('.settings-tab').forEach(t => t.classList.remove('active'));
      $$('.settings-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      $(`[data-panel="${target}"]`)?.classList.add('active');
    });
  });
}

// ─── Revenue Chart ──────────────────────────────────
let revenueChart = null;
function initRevenueChart(data) {
  const ctx = $('#revenue-chart');
  if (!ctx || !window.Chart) return;
  if (revenueChart) revenueChart.destroy();
  revenueChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Revenue (৳)',
        data: data.values,
        borderColor: '#c9a84c',
        backgroundColor: 'rgba(201,168,76,0.08)',
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#c9a84c',
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { backgroundColor: '#18181d', titleColor: '#e8e8ec', bodyColor: '#888896', borderColor: '#232329', borderWidth: 1 }},
      scales: {
        x: { grid: { color: '#232329' }, ticks: { color: '#888896', font: { size: 11 } }},
        y: { grid: { color: '#232329' }, ticks: { color: '#888896', font: { size: 11 }, callback: v => '৳' + v }}
      }
    }
  });
}

function initOrdersBarChart(data) {
  const ctx = $('#orders-chart');
  if (!ctx || !window.Chart) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Orders',
        data: data.values,
        backgroundColor: ['rgba(201,168,76,.7)', 'rgba(41,128,185,.7)', 'rgba(39,174,96,.7)', 'rgba(231,76,60,.7)', 'rgba(243,156,18,.7)'],
        borderRadius: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }},
      scales: { x: { grid: { display: false }, ticks: { color: '#888896' }}, y: { grid: { color: '#232329' }, ticks: { color: '#888896' }}}
    }
  });
}

function initCategoryChart(data) {
  const ctx = $('#category-chart');
  if (!ctx || !window.Chart) return;
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.labels,
      datasets: [{ data: data.values, backgroundColor: ['#c9a84c','#2980b9','#27ae60','#e74c3c','#9b59b6'], borderWidth: 0 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#888896', padding: 16, font: { size: 11 } }}
      },
      cutout: '65%'
    }
  });
}

// ─── Date range filter ──────────────────────────────
function initDateRangeFilter() {
  $$('.date-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const group = pill.closest('.date-range-pills');
      $$('.date-pill', group).forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const range = pill.dataset.range;
      // Trigger a page reload with the range param
      const url = new URL(window.location.href);
      url.searchParams.set('range', range);
      if (typeof initRevenueChart === 'function') {
        window.location.href = url.toString();
      }
    });
  });
}

// ─── CSV Export ─────────────────────────────────────
function exportTableCSV(tableId, filename) {
  const table = $(`#${tableId}`);
  if (!table) return;
  const rows = $$('tr', table);
  const csv = rows.map(row =>
    $$('th, td', row)
      .filter((_, i) => i > 0) // skip checkbox col
      .map(cell => `"${cell.textContent.trim().replace(/"/g, '""')}"`)
      .join(',')
  ).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}

// ─── Init ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  adminTheme.load();
  sidebar.init();
  omnibar.init();
  initTableSort();
  initTableSearch();
  initBulkSelect();
  initSessionTimer();
  initSettingsTabs();
  initDateRangeFilter();

  // Theme toggle button
  $('#theme-toggle-btn')?.addEventListener('click', () => adminTheme.toggle());

  // Auto-dismiss alerts
  setTimeout(() => {
    $$('.admin-alerts .admin-alert').forEach(el => {
      el.style.transition = '.4s'; el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    });
  }, 5000);
});
