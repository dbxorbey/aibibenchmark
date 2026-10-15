// Run via chrome-devtools evaluate_script right after navigating to a published dashboard
// (navigate with initScript: performance.setResourceTimingBufferSize(10000);)
// Waits until no new dashboard-query requests appear for 5s, then reports timings relative to navigation start.
async () => {
  const isQ = e => e.name.includes('/lakeview-query/');
  let last = -1, stable = 0; const t0 = Date.now();
  while (Date.now() - t0 < 240000) {
    const n = performance.getEntriesByType('resource').filter(isQ).length;
    if (n === last && n > 0) { stable += 500; if (stable >= 5000) break; } else { stable = 0; last = n; }
    await new Promise(r => setTimeout(r, 500));
  }
  const es = performance.getEntriesByType('resource').filter(isQ);
  const tokens = new Set();
  es.forEach(e => new URL(e.name).searchParams.getAll('tokens').forEach(t => tokens.add(t)));
  es.filter(e => e.name.includes('query-results/')).forEach(e => tokens.add(e.name.split('query-results/')[1].split('?')[0]));
  return {
    n_requests: es.length,
    n_queries_seen: tokens.size,
    first_query_submit_s: +(Math.min(...es.map(e => e.startTime)) / 1000).toFixed(2),
    all_data_loaded_s: +(Math.max(...es.map(e => e.responseEnd)) / 1000).toFixed(2),
  };
}
