/* ═══════════════════════════════════════════════════════
   PROCUREDATA  –  Dashboard Script
   ═══════════════════════════════════════════════════════ */

'use strict';

/* ── Live clock ──────────────────────────────────────── */
(function startClock() {
  const el = document.getElementById('topbarTime');
  if (!el) return;
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  tick();
  setInterval(tick, 1000);
})();

/* ── Sidebar toggle (mobile) ─────────────────────────── */
document.getElementById('menuToggle')?.addEventListener('click', () => {
  document.getElementById('sidebar')?.classList.toggle('open');
});

/* ── Tab / panel switching ───────────────────────────── */
const TAB_LABELS = { sam: 'SAM.gov', septa: 'SEPTA' };

document.querySelectorAll('.nav-item[data-tab]').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.getAttribute('data-tab');

    // Update sidebar active state
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Show matching panel
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`${tab}-panel`);
    if (panel) panel.classList.add('active');

    // Update breadcrumb
    const bc = document.getElementById('bcCurrent');
    if (bc) bc.textContent = TAB_LABELS[tab] ?? tab;

    // Close mobile sidebar
    document.getElementById('sidebar')?.classList.remove('open');
  });
});

/* ══════════════════════════════════════════════════════
   PROGRESS STEPPER HELPER
   Steps: s1 → s2 → s3 → s4 → s5
   Each step ID pattern:  {prefix}-s1 … {prefix}-s5
   ══════════════════════════════════════════════════════ */

/**
 * @param {string} prefix   'sam' | 'septa'
 * @param {number} upTo     1-5  — advance all steps ≤ upTo to "done",
 *                                 set upTo to "active", rest stay "pending"
 */
function setSteps(prefix, upTo) {
  for (let i = 1; i <= 5; i++) {
    const row  = document.getElementById(`${prefix}-s${i}`);
    const icon = row?.querySelector('.step-icon');
    if (!row || !icon) continue;

    row.classList.remove('active', 'done');
    icon.classList.remove('active', 'done', 'pending');

    if (i < upTo) {
      row.classList.add('done');
      icon.classList.add('done');
    } else if (i === upTo) {
      row.classList.add('active');
      icon.classList.add('active');
    } else {
      icon.classList.add('pending');
    }
  }
}

function setStatusMsg(prefix, msg) {
  const el = document.getElementById(`${prefix}-status-msg`);
  if (el) el.textContent = msg;
}

/* ── Elapsed timer ───────────────────────────────────── */
function makeTimer(elapsedId) {
  const el = document.getElementById(elapsedId);
  let seconds = 0;
  let handle = null;

  return {
    start() {
      seconds = 0;
      if (el) el.textContent = '00:00';
      handle = setInterval(() => {
        seconds++;
        const m = String(Math.floor(seconds / 60)).padStart(2, '0');
        const s = String(seconds % 60).padStart(2, '0');
        if (el) el.textContent = `${m}:${s}`;
      }, 1000);
    },
    stop() {
      if (handle) clearInterval(handle);
    }
  };
}

/* ══════════════════════════════════════════════════════
   GENERIC SCRAPE HANDLER
   ══════════════════════════════════════════════════════ */

/**
 * @param {Object} opts
 *   prefix       — 'sam' | 'septa'
 *   endpoint     — '/scrape_sam' | '/scrape_septa'
 *   body         — JSON payload object
 *   btnId        — button element id
 *   loaderId     — spinner element id
 *   btnTextOrig  — original button label
 *   dlLinkId     — download <a> element id
 *   elapsedId    — elapsed timer element id
 *   stepMsgs     — array[5] of status messages per step
 *   stepDelays   — array[4] of delays (ms) between steps 1→2, 2→3, 3→4, 4→5
 */
async function runScraper(opts) {
  const {
    prefix, endpoint, body,
    btnId, loaderId, btnTextOrig,
    dlLinkId, elapsedId,
    stepMsgs, stepDelays
  } = opts;

  const btn        = document.getElementById(btnId);
  const btnText    = btn?.querySelector('.btn-text');
  const spinner    = document.getElementById(loaderId);
  const progressEl = document.getElementById(`${prefix}-progress`);
  const resultEl   = document.getElementById(`${prefix}-result`);
  const errorEl    = document.getElementById(`${prefix}-error`);
  const resultMsg  = document.getElementById(`${prefix}-result-msg`);
  const errorMsg   = document.getElementById(`${prefix}-error-msg`);
  const dlLink     = document.getElementById(dlLinkId);

  // ── Reset UI state ────────────────────────────────────
  progressEl?.classList.add('hidden');
  resultEl?.classList.add('hidden');
  errorEl?.classList.add('hidden');
  setSteps(prefix, 1);

  // ── Show loading state ────────────────────────────────
  if (btn)     btn.disabled = true;
  if (btnText) btnText.textContent = 'Processing…';
  if (spinner) spinner.style.display = 'block';

  // ── Show progress panel ───────────────────────────────
  progressEl?.classList.remove('hidden');
  setSteps(prefix, 1);
  setStatusMsg(prefix, stepMsgs[0]);

  const timer = makeTimer(elapsedId);
  timer.start();

  // ── Simulate step progression while server works ──────
  const stepTimers = [];
  let currentStep = 1;

  for (let i = 0; i < stepDelays.length; i++) {
    const step = i + 2;  // steps 2, 3, 4, 5
    const t = setTimeout(() => {
      if (currentStep < step) {
        currentStep = step;
        setSteps(prefix, step);
        setStatusMsg(prefix, stepMsgs[step - 1]);
      }
    }, stepDelays[i]);
    stepTimers.push(t);
  }

  // ── Hit the server ────────────────────────────────────
  try {
    const resp = await fetch(endpoint, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body)
    });

    const data = await resp.json();
    stepTimers.forEach(clearTimeout);   // cancel pending step advances
    timer.stop();

    if (data.success) {
      // Complete all steps as "done"
      for (let s = 1; s <= 5; s++) {
        const row  = document.getElementById(`${prefix}-s${s}`);
        const icon = row?.querySelector('.step-icon');
        row?.classList.remove('active', 'pending');
        row?.classList.add('done');
        icon?.classList.remove('active', 'pending');
        icon?.classList.add('done');
      }
      progressEl?.classList.add('hidden');

      // Show result
      if (resultMsg) resultMsg.textContent = `Saved as: ${data.filename}`;
      if (dlLink)    dlLink.href = `/download/${data.filename}`;
      resultEl?.classList.remove('hidden');
    } else {
      progressEl?.classList.add('hidden');
      if (errorMsg) errorMsg.textContent = data.error ?? 'The server returned an error.';
      errorEl?.classList.remove('hidden');
    }

  } catch (err) {
    stepTimers.forEach(clearTimeout);
    timer.stop();
    progressEl?.classList.add('hidden');
    if (errorMsg) errorMsg.textContent = `Network error: ${err.message}`;
    errorEl?.classList.remove('hidden');

  } finally {
    if (btn)     btn.disabled = false;
    if (btnText) btnText.textContent = btnTextOrig;
    if (spinner) spinner.style.display = 'none';
  }
}

/* ══════════════════════════════════════════════════════
   SAM.gov LISTENER
   ══════════════════════════════════════════════════════ */
document.getElementById('scrapeSamBtn')?.addEventListener('click', () => {
  const dateFilter = document.getElementById('date_filter')?.value?.trim();

  if (!dateFilter) {
    // Highlight the date field
    const inp = document.getElementById('date_filter');
    if (inp) {
      inp.style.borderColor = '#dc2626';
      inp.style.boxShadow   = '0 0 0 3px rgba(220,38,38,.15)';
      inp.focus();
      setTimeout(() => {
        inp.style.borderColor = '';
        inp.style.boxShadow   = '';
      }, 2500);
    }
    return;
  }

  runScraper({
    prefix:      'sam',
    endpoint:    '/scrape_sam',
    body:        { date_filter: dateFilter },
    btnId:       'scrapeSamBtn',
    loaderId:    'samLoader',
    btnTextOrig: 'Start SAM Scraping',
    dlLinkId:    'samDownloadLink',
    elapsedId:   'sam-elapsed',
    stepMsgs: [
      'Launching Chrome and loading dependencies…',
      'Navigating to SAM.gov search with your date filter…',
      'Iterating through result pages, applying set-aside filters…',
      'Visiting each bid's detail page and extracting 9 fields…',
      'Writing extracted rows to CSV file…'
    ],
    stepDelays: [3000, 10000, 25000, 55000]
  });
});

/* ══════════════════════════════════════════════════════
   SEPTA LISTENER
   ══════════════════════════════════════════════════════ */
document.getElementById('scrapeSeptaBtn')?.addEventListener('click', () => {
  const dateFilter = document.getElementById('septa_date_filter')?.value?.trim();

  runScraper({
    prefix:      'septa',
    endpoint:    '/scrape_septa',
    body:        { date_filter: dateFilter },
    btnId:       'scrapeSeptaBtn',
    loaderId:    'septaLoader',
    btnTextOrig: 'Start SEPTA Scraping',
    dlLinkId:    'septaDownloadLink',
    elapsedId:   'septa-elapsed',
    stepMsgs: [
      'Launching Chrome and loading dependencies…',
      'Logging into SEPTA EPS Admin portal…',
      'Navigating to Open Quotes section…',
      'Extracting quote details row by row…',
      'Writing data to Excel (.xlsx) file…'
    ],
    stepDelays: [3000, 8000, 15000, 30000]
  });
});

/* ══════════════════════════════════════════════════════
   LEGACY listeners (UNISON / DIBBS) kept for compatibility
   ══════════════════════════════════════════════════════ */
document.getElementById('scrapeUnisonBtn')?.addEventListener('click', () => {
  const filterBy = document.getElementById('unison_filter')?.value;
  fetch('/scrape_unison', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ filter_by: filterBy })
  });
});

document.getElementById('scrapeDibbsBtn')?.addEventListener('click', () => {
  fetch('/scrape_dibbs', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({})
  });
});
