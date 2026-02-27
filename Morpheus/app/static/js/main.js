/**
 * FinAI Personal Finance Manager — Main JavaScript
 * Helper utilities for AJAX form submissions, toasts, and UI utilities
 */

/* ── Toast Notification ─────────────────────────────────────────────────── */
function showToast(msg, type = 'info', duration = 4000) {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity .3s';
    setTimeout(() => el.remove(), 300);
  }, duration);
}

/* ── Generic AJAX Form Submit ───────────────────────────────────────────── */
async function submitForm(formId, endpoint, resultContainerId, renderFn) {
  const form = document.getElementById(formId);
  if (!form) { showToast(`Form #${formId} not found`, 'error'); return null; }

  const data = new FormData(form);
  try {
    const resp = await fetch(endpoint, { method: 'POST', body: data });
    const json = await resp.json();
    if (resultContainerId && renderFn) {
      renderFn(json, document.getElementById(resultContainerId));
    }
    return json;
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
    return null;
  }
}

/* ── Confidence Badge ───────────────────────────────────────────────────── */
function showConfidenceBadge(confidence) {
  const pct = Math.round((confidence ?? 0) * 100);
  const cls = pct >= 85 ? 'conf-high' : pct >= 60 ? 'conf-mid' : 'conf-low';
  return `<span class="confidence-badge ${cls}">${pct}%</span>`;
}

/* ── Anomaly Severity Badge ─────────────────────────────────────────────── */
function renderAnomalySeverityBadge(severity) {
  const map = {
    critical: ['badge-red',    '🔴'],
    high:     ['badge-orange', '🟠'],
    medium:   ['badge-yellow', '🟡'],
    low:      ['badge-green',  '🟢'],
    none:     ['badge-blue',   '⚪'],
  };
  const [cls, emoji] = map[severity] || map.none;
  return `<span class="badge ${cls}">${emoji} ${severity}</span>`;
}

/* ── Anomaly Result Panel ───────────────────────────────────────────────── */
function renderAnomalyResult(data, container) {
  if (!container) return;
  if (!data?.success) {
    container.innerHTML = `<div class="error-box">❌ ${data?.error ?? 'Unknown error'}</div>`;
    return;
  }
  const r = data.result ?? data;
  const isAnomalous = r.is_anomaly;
  const sev = r.severity ?? 'none';
  const score = r.anomaly_score ?? 0;

  container.innerHTML = `
    <div class="anomaly-verdict ${isAnomalous ? 'anomaly-yes' : 'anomaly-no'}">
      <span class="verdict-icon">${isAnomalous ? '🚨' : '✅'}</span>
      <span>${isAnomalous ? 'ANOMALY DETECTED' : 'TRANSACTION NORMAL'}</span>
    </div>
    <div class="result-grid" style="margin-top:12px;">
      <div class="result-item">
        <span class="result-label">Severity</span>
        ${renderAnomalySeverityBadge(sev)}
      </div>
      <div class="result-item">
        <span class="result-label">Anomaly Score</span>
        <span class="result-value">${score.toFixed(4)}</span>
      </div>
    </div>
  `;
}

/* ── Number Formatting ──────────────────────────────────────────────────── */
function formatINR(amount) {
  if (amount === null || amount === undefined) return '—';
  return '₹' + Math.abs(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function formatPct(value, decimals = 1) {
  if (value === null || value === undefined) return '—';
  return (value * 100).toFixed(decimals) + '%';
}

/* ── Plotly Helpers ─────────────────────────────────────────────────────── */
const PLOTLY_DEFAULT_LAYOUT = {
  paper_bgcolor: 'transparent',
  plot_bgcolor:  'transparent',
  font: { color: '#374151', size: 11, family: 'Inter, sans-serif' },
  margin: { t: 40, b: 40, l: 50, r: 20 },
  showlegend: false,
};

function renderBarChart(containerId, labels, values, title, colors) {
  if (!window.Plotly) return;
  Plotly.newPlot(containerId, [{
    type: 'bar',
    x: labels,
    y: values,
    marker: { color: colors ?? '#6366f1' },
    text: values.map(v => v.toFixed(1)),
    textposition: 'auto',
  }], {
    ...PLOTLY_DEFAULT_LAYOUT,
    title: { text: title, font: { size: 13 } },
  }, { responsive: true, displayModeBar: false });
}

function renderPieChart(containerId, labels, values, title) {
  if (!window.Plotly) return;
  Plotly.newPlot(containerId, [{
    type: 'pie',
    labels,
    values,
    hole: 0.4,
    marker: { colors: ['#6366f1','#10b981','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#f97316','#14b8a6','#ec4899','#64748b'] },
    textinfo: 'label+percent',
    textfont: { size: 11 },
  }], {
    ...PLOTLY_DEFAULT_LAYOUT,
    title: { text: title, font: { size: 13 } },
    margin: { t: 40, b: 20, l: 20, r: 20 },
  }, { responsive: true, displayModeBar: false });
}

/* ── User Switcher ──────────────────────────────────────────────────────── */
function initUserSwitcher(selectId, baseUrl = '/dashboard') {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.addEventListener('change', () => {
    window.location.href = `${baseUrl}?user_id=${sel.value}`;
  });
}

/* ── Loading State Helpers ──────────────────────────────────────────────── */
function setLoading(buttonEl, loading, originalText) {
  if (!buttonEl) return;
  if (loading) {
    buttonEl._origText = buttonEl.textContent;
    buttonEl.disabled = true;
    buttonEl.textContent = '⏳ Processing…';
  } else {
    buttonEl.disabled = false;
    buttonEl.textContent = originalText ?? buttonEl._origText ?? 'Submit';
  }
}

/* ── Retrain Helper ─────────────────────────────────────────────────────── */
async function retrainModel(endpoint, btnEl) {
  if (!confirm('Retrain the model? This may take a moment.')) return;
  setLoading(btnEl, true);
  try {
    const resp = await fetch(endpoint, { method: 'POST' });
    const json = await resp.json();
    showToast('✅ Retrained! ' + (json.report ?? json.message ?? ''), 'success');
  } catch(e) {
    showToast('❌ Retrain failed: ' + e.message, 'error');
  } finally {
    setLoading(btnEl, false);
  }
}

/* ── Dashboard Initializer ──────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Mark active nav link
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href && path.startsWith(href) && href !== '/') {
      a.classList.add('active');
    }
  });

  // Init user switcher on dashboard
  initUserSwitcher('userSelect', '/dashboard');
});
