/* Subvalore – Phase 1 placeholder frontend
   Full data rendering will be wired in Phase 4.
   This file sets up the search/tab scaffold and health check. */

const API = "";  // same origin

const TAB_LABELS = [
  ["price_history",             "Price History"],
  ["pe",                        "P/E Ratio"],
  ["dividend_yield",            "Dividend Yield"],
  ["dividend_history",          "Dividend History"],
  ["market_cap",                "Market Cap"],
  ["volume",                    "Volume"],
  ["volume_avg",                "Avg Volume"],
  ["volume_avg_10",             "Avg Vol 10d"],
  ["income_statement",          "Income Stmt"],
  ["quarterly_income_statement","Quarterly Income"],
  ["balance_sheet",             "Balance Sheet"],
  ["earnings_dates",            "Earnings Dates"],
  ["calendar",                  "Calendar"],
  ["recommendations",           "Recommendations"],
  ["price_targets",             "Price Targets"],
  ["earnings_estimate",         "Earnings Est."],
  ["revenue_estimate",          "Revenue Est."],
  ["eps_trend",                 "EPS Trend"],
  ["growth_estimates",          "Growth Est."],
  ["insider_purchases",         "Insider Purchases"],
  ["insider_transactions",      "Insider Transactions"],
  ["news",                      "News"],
];

// ── DOM refs ────────────────────────────────────────────────────────
const searchForm    = document.getElementById("search-form");
const tickerInput   = document.getElementById("ticker-input");
const searchHint    = document.getElementById("search-hint");
const statusBar     = document.getElementById("status-bar");
const dashboard     = document.getElementById("dashboard");
const tabNav        = document.getElementById("tab-nav");
const tabContent    = document.getElementById("tab-content");

// ── State ───────────────────────────────────────────────────────────
let currentSymbol = null;
let currentData   = null;

// ── Bootstrap tabs ──────────────────────────────────────────────────
function buildTabs() {
  tabNav.innerHTML     = "";
  tabContent.innerHTML = "";

  TAB_LABELS.forEach(([key, label], i) => {
    const btn = document.createElement("button");
    btn.className  = "tab-btn" + (i === 0 ? " active" : "");
    btn.textContent = label;
    btn.dataset.tab = key;
    btn.addEventListener("click", () => switchTab(key));
    tabNav.appendChild(btn);

    const panel = document.createElement("div");
    panel.className = "tab-panel" + (i === 0 ? " active" : "");
    panel.id = `panel-${key}`;
    panel.innerHTML = loading();
    tabContent.appendChild(panel);
  });
}

function switchTab(key) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === key));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("active", p.id === `panel-${key}`));
  if (currentData) renderTab(key, currentData);
}

// ── Search ──────────────────────────────────────────────────────────
searchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const symbol = tickerInput.value.trim().toUpperCase();
  if (!symbol) return;
  await loadTicker(symbol);
});

async function loadTicker(symbol) {
  currentSymbol = symbol;
  currentData   = null;
  searchHint.textContent = "";

  showDashboard(false);
  showStatus(false);

  // Show loading state in all panels
  buildTabs();
  showDashboard(true);
  setAllPanelsLoading();

  try {
    const resp = await fetch(`${API}/api/ticker/${symbol}/all`);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    currentData = await resp.json();
    renderAll(currentData);
    renderStatusBar(currentData);
    showStatus(true);
  } catch (err) {
    setAllPanelsError(err.message);
    searchHint.textContent = `Error: ${err.message}`;
  }
}

// ── Render ──────────────────────────────────────────────────────────
function renderAll(data) {
  TAB_LABELS.forEach(([key]) => renderTab(key, data));
}

function renderTab(key, data) {
  const panel = document.getElementById(`panel-${key}`);
  if (!panel) return;

  switch (key) {
    case "price_history":            panel.innerHTML = renderPriceHistory(data.price_history); break;
    case "pe":                       panel.innerHTML = renderScalar("Forward P/E", data.metrics?.pe); break;
    case "dividend_yield":           panel.innerHTML = renderScalar("Dividend Yield", data.metrics?.dividend_yield, v => fmt(v, 4)); break;
    case "dividend_history":         panel.innerHTML = renderDividendHistory(data.dividend_history); break;
    case "market_cap":               panel.innerHTML = renderScalar("Market Cap", data.metrics?.market_cap, fmtBig); break;
    case "volume":                   panel.innerHTML = renderScalar("Volume", data.metrics?.volume, fmtBig); break;
    case "volume_avg":               panel.innerHTML = renderScalar("Average Volume", data.metrics?.volume_avg, fmtBig); break;
    case "volume_avg_10":            panel.innerHTML = renderScalar("Avg Volume 10d", data.metrics?.volume_avg_10, fmtBig); break;
    case "income_statement":         panel.innerHTML = renderDataset(data.income_statement); break;
    case "quarterly_income_statement": panel.innerHTML = renderDataset(data.quarterly_income_statement); break;
    case "balance_sheet":            panel.innerHTML = renderDataset(data.balance_sheet); break;
    case "earnings_dates":           panel.innerHTML = renderDataset(data.earnings_dates); break;
    case "calendar":                 panel.innerHTML = renderCalendar(data.calendar); break;
    case "recommendations":          panel.innerHTML = renderRecommendations(data.recommendations); break;
    case "price_targets":            panel.innerHTML = renderPriceTargets(data.price_targets); break;
    case "earnings_estimate":        panel.innerHTML = renderDataset(data.earnings_estimate); break;
    case "revenue_estimate":         panel.innerHTML = renderDataset(data.revenue_estimate); break;
    case "eps_trend":                panel.innerHTML = renderDataset(data.eps_trend); break;
    case "growth_estimates":         panel.innerHTML = renderDataset(data.growth_estimates); break;
    case "insider_purchases":        panel.innerHTML = renderDataset(data.insider_purchases); break;
    case "insider_transactions":     panel.innerHTML = renderDataset(data.insider_transactions); break;
    case "news":                     panel.innerHTML = renderNews(data.news); break;
    default:                         panel.innerHTML = empty("No renderer for this dataset yet.");
  }
}

// ── Individual renderers ────────────────────────────────────────────
function renderScalar(label, value, formatter = fmt) {
  if (value === null || value === undefined)
    return empty(`${label} data not available.`);
  return `
    <div class="metric-grid">
      <div class="metric-card">
        <div class="label">${esc(label)}</div>
        <div class="value">${esc(String(formatter(value)))}</div>
      </div>
    </div>`;
}

function renderPriceHistory(rows) {
  if (!rows || rows.length === 0) return empty("No price history available.");
  const cols = ["timestamp","open","high","low","close","volume","dividends","stock_splits"];
  return tableFrom(rows, cols);
}

function renderDividendHistory(rows) {
  if (!rows || rows.length === 0) return empty("No dividend history available.");
  return tableFrom(rows, ["date","value"]);
}

function renderDataset(payload) {
  if (!payload) return empty("Data not available.");

  // If it's an array of objects
  if (Array.isArray(payload) && payload.length > 0 && typeof payload[0] === "object") {
    return tableFrom(payload, Object.keys(payload[0]));
  }

  // If it's a dict-of-dicts (column -> {index -> value})
  if (typeof payload === "object" && !Array.isArray(payload)) {
    const cols = Object.keys(payload);
    if (cols.length === 0) return empty("No data.");
    const firstCol = payload[cols[0]];
    if (typeof firstCol === "object" && !Array.isArray(firstCol)) {
      const rows_keys = Object.keys(firstCol);
      const rows = rows_keys.map(rk => {
        const row = { "": rk };
        cols.forEach(c => { row[c] = payload[c][rk]; });
        return row;
      });
      return tableFrom(rows, ["", ...cols]);
    }
  }

  // Fallback: pretty-print object as key/value table
  if (typeof payload === "object") {
    const entries = Object.entries(payload);
    if (entries.length === 0) return empty("No data.");
    return tableFrom(entries.map(([k, v]) => ({ key: k, value: v })), ["key","value"]);
  }

  return empty("Unsupported data format.");
}

function renderCalendar(payload) {
  if (!payload || Object.keys(payload).length === 0) return empty("No calendar data available.");
  const rows = Object.entries(payload).map(([k, v]) => ({ key: k, value: Array.isArray(v) ? v.join(", ") : v }));
  return tableFrom(rows, ["key","value"]);
}

function renderRecommendations(rows) {
  if (!rows || rows.length === 0) return empty("No recommendations available.");
  const cols = ["period","strong_buy","buy","hold","sell","strong_sell"];
  return tableFrom(rows, cols);
}

function renderPriceTargets(pt) {
  if (!pt) return empty("No price target data available.");
  const fields = ["current","low","high","mean","median"];
  return `
    <div class="metric-grid">
      ${fields.map(f => `
        <div class="metric-card">
          <div class="label">${esc(f.replace(/_/g," "))}</div>
          <div class="value">${pt[f] != null ? "$" + fmt(pt[f]) : "—"}</div>
        </div>`).join("")}
    </div>`;
}

function renderNews(items) {
  if (!items || items.length === 0) return empty("No news available.");
  return `<div class="news-grid">` +
    items.map(n => `
      <div class="news-card">
        <div class="news-title">
          ${n.url ? `<a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title || "Untitled")}</a>` : esc(n.title || "Untitled")}
        </div>
        <div class="news-meta">
          ${n.publisher ? `<span>${esc(n.publisher)}</span>` : ""}
          ${n.published_at ? `<span>${fmtDate(n.published_at)}</span>` : ""}
        </div>
        ${n.summary ? `<div class="news-summary">${esc(n.summary)}</div>` : ""}
      </div>`).join("") +
    `</div>`;
}

// ── Generic table helper ─────────────────────────────────────────────
function tableFrom(rows, cols) {
  if (!rows || rows.length === 0) return empty("No data.");
  return `
    <div class="data-table-wrap">
      <table>
        <thead><tr>${cols.map(c => `<th>${esc(String(c))}</th>`).join("")}</tr></thead>
        <tbody>
          ${rows.map(r => `<tr>${cols.map(c => `<td>${fmtCell(r[c])}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

// ── Status bar ───────────────────────────────────────────────────────
function renderStatusBar(data) {
  const sym  = data.symbol || currentSymbol;
  const name = data.company_name || "";
  const ts   = data.last_refreshed_at ? `Last updated: ${fmtDate(data.last_refreshed_at)}` : "";

  statusBar.innerHTML = `
    <span class="symbol">${esc(sym)}</span>
    ${name ? `<span class="company-name">${esc(name)}</span>` : ""}
    <span class="last-updated">${esc(ts)}</span>
    <button class="refresh-btn" onclick="forceRefresh()">↻ Refresh</button>`;
}

async function forceRefresh() {
  if (!currentSymbol) return;
  searchHint.textContent = "Refreshing data from yfinance…";
  try {
    const resp = await fetch(`${API}/api/ticker/${currentSymbol}/refresh`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    searchHint.textContent = "";
    await loadTicker(currentSymbol);
  } catch (err) {
    searchHint.textContent = `Refresh failed: ${err.message}`;
  }
}

// ── Utilities ────────────────────────────────────────────────────────
function loading()   { return `<div class="state-msg"><div class="spinner"></div> Loading…</div>`; }
function empty(msg)  { return `<div class="state-msg">${esc(msg)}</div>`; }
function error_(msg) { return `<div class="state-msg" style="color:var(--red)">⚠ ${esc(msg)}</div>`; }

function setAllPanelsLoading() {
  document.querySelectorAll(".tab-panel").forEach(p => { p.innerHTML = loading(); });
}
function setAllPanelsError(msg) {
  document.querySelectorAll(".tab-panel").forEach(p => { p.innerHTML = error_(msg); });
}

function showDashboard(show) { dashboard.classList.toggle("hidden", !show); }
function showStatus(show)    { statusBar.classList.toggle("hidden", !show); }

function esc(str) {
  if (str === null || str === undefined) return "—";
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function fmt(v, decimals = 2) {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  return isNaN(n) ? String(v) : n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtBig(v) {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (isNaN(n)) return String(v);
  if (n >= 1e12) return (n / 1e12).toFixed(2) + "T";
  if (n >= 1e9)  return (n / 1e9).toFixed(2) + "B";
  if (n >= 1e6)  return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3)  return (n / 1e3).toFixed(2) + "K";
  return n.toLocaleString();
}

function fmtDate(str) {
  if (!str) return "";
  try { return new Date(str).toLocaleString(); } catch { return str; }
}

function fmtCell(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return esc(JSON.stringify(v));
  const n = Number(v);
  if (!isNaN(n) && v !== "" && v !== true && v !== false) return fmt(n);
  return esc(String(v));
}
