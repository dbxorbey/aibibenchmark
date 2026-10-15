// Run via chrome-devtools evaluate_script on a loaded, published dashboard (after ./invalidate.sh).
// Clicks the dashboard's Refresh button and reports the time from the click until the last dashboard-query response
// (waits until no new dashboard-query requests appear for 10s - long-poll requests take ~5s).
async () => {
  const isQ = e => e.name.includes('/lakeview-query/');
  const btn = [...document.querySelectorAll('button')].find(b => /^Refresh/.test(b.getAttribute('aria-label') || ''));
  if (!btn) return { error: 'Refresh button not found' };
  performance.setResourceTimingBufferSize(10000);
  performance.clearResourceTimings();
  const tClick = performance.now();
  btn.click();
  const qs = () => performance.getEntriesByType('resource').filter(e => isQ(e) && e.startTime >= tClick);
  let last = -1, stable = 0; const t0 = Date.now();
  while (Date.now() - t0 < 240000) {
    const n = qs().length;
    if (n === last && n > 0) { stable += 500; if (stable >= 10000) break; } else { stable = 0; last = n; }
    await new Promise(r => setTimeout(r, 500));
  }
  const es = qs();
  return {
    n_requests: es.length,
    all_data_loaded_s: +((Math.max(...es.map(e => e.responseEnd)) - tClick) / 1000).toFixed(2),
  };
}
