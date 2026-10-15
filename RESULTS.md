# Results – AI/BI dashboard performance benchmark (2026-10-14, verified, n=10)

Setup and methodology: see `README.md`. Warehouses: serverless PRO Small (1 cluster) for steps 0–5,
Lakehouse//RT Small (1 cluster) for step 6. Data: 10M fact rows, 7 tables.

## 1. Main table (steps are cumulative) – mean ± standard deviation, n=10 per cell

| Step | Change | Queries on landing-page load | **Replay first load** (s, no result cache) | Replay subsequent load (s, result cache) | Replay first load vs baseline | **Browser first load** (s, caches invalidated, Refresh) | Browser subsequent load (s, page reload) |
|---|---|---:|---:|---:|---:|---:|---:|
| 0 | Baseline – star schema, joins + LOD SQL in each of 12 datasets | 28 | **7.70 ± 0.54** | 2.42 ± 0.41 | 100% | **9.43 ± 1.05** | 2.36 ± 0.34 |
| 1 | One pre-joined wide table | 28 | **4.72 ± 0.53** | 1.80 ± 0.58 | 61% | **5.05 ± 0.61** | 2.28 ± 0.30 |
| 2 | Metric view with parameters | 28 | **5.21 ± 0.69** | 1.60 ± 0.15 | 68% | **5.51 ± 0.67** | 2.55 ± 0.54 |
| 3 | Materialized grain (product × country × week) | 28 | **3.91 ± 0.44** | 2.26 ± 0.28 | 51% | **4.96 ± 0.58** | 2.24 ± 0.14 |
| 4 | Fewer widgets on page 1 (1 chart instead of 12) | 17 | **2.14 ± 0.45** | 1.19 ± 0.27 | 28% | **3.73 ± 0.28** | 2.38 ± 0.46 |
| 5 | Ignored filters (dropdowns not fed from the 10M-row table) | 17 | **2.16 ± 0.40** | 1.27 ± 0.41 ³ | 28% | **2.94 ± 0.47** | 1.92 ± 0.22 |
| 6 | Lakehouse//RT warehouse | 17 | **0.36 ± 0.14** | 0.35 ± 0.17 | 5% | **0.96 ± 0.22** ¹ | 2.03 ± 0.69 ² |
| ref | Baseline (step 0) on Lakehouse//RT | 28 | 2.61 ± 0.41 | 2.47 ± 0.25 | 34% | – | – |

¹ On a running RT warehouse; the first refresh after ~25 min idle took 2.06 s (not included).
² Includes one 3.93 s reload after the RT warehouse had been idle ~15 min (other runs 1.54–2.06 s).
³ Excluding one 13.12 s outlier (run 7 of 10, a single hiccup with all results served from cache); incl. it 2.46 ± 3.76 s, median 1.11 s.

**Runs:** 3 runs per cell from the first session + 7 runs added on 2026-10-14 (16:00–17:15) with the same scripts and
warehouses (browser first loads of the first session had 2–3 runs, topped up to 10). Replay step 0 on PRO: the first 7
added runs were made right after the warehouse resumed from auto-stop (cold disk cache, 15.5 → 7.5 s decreasing) and
were replaced with 7 runs on the warm warehouse. Browser first load in runs 4–10 = time from the
click on Refresh until the last `lakeview-query` response (`browser/refresh_measure.js`).

Standard deviation = sample standard deviation over the runs. Individual runs: `results/replay_*.json`
(`first_load_s`, `subsequent_load_s`) and `results/browser_*.json` (`first_load_runs_s`, `subsequent_load_runs_s`);
per-run browser log of runs 4–10: `results/browser_runs_extra.jsonl`.

## 2. Effect of each step on its own (vs previous step, based on means, n=10)

Welch t-statistic in brackets; |t| ≳ 2.1 means significant at 5% for n=10 vs n=10.

| Step | Replay first load | Browser first load | Comment |
|---|---:|---:|---|
| 1 Pre-joined table | −39% (7.70 → 4.72, t=−12) | −46% (9.43 → 5.05, t=−11) | Largest modelling gain. Single main-chart query: 7-table star 2.63 s, star without the 2M-row customer dim 2.23 s, wide table 1.77 s – the customer join is ~half of the join cost, the 5 small dims the rest. Filter dropdowns also no longer join 7 tables. |
| 2 Metric view w/ parameters | +10% (4.72 → 5.21, t=+1.8) | +9% (5.05 → 5.51, t=+1.6) | **Not a speed feature** – slightly slower, not significant. Same work plus a semantic layer; LOD logic must sit in the parameterized `source` (nested aggregation). Benefit: governed, reusable metric definitions. Parameterized metric views cannot be materialized. |
| 3 Materialized grain | −25% (5.21 → 3.91, t=−5.0) | −10% (5.51 → 4.96, t=−2.0, borderline) | Chart queries get faster (772k instead of 10M rows; main chart 3.95 → 2.74 s under load), but the 16 filter-dropdown queries still scan the 10M-row table and mask most of it in the browser. |
| 4 Fewer widgets on page 1 | −45% (3.91 → 2.14, t=−8.9) | −25% (4.96 → 3.73, t=−6.0) | 11 chart queries fewer → much less queueing on the single cluster. Verified: only 18 queries run on load; the Deep Dive charts run only when that page is opened. |
| 5 Ignored filters | ±0% (2.14 → 2.16, t=+0.1) | **−21% (3.73 → 2.94, t=−4.6)** | **Significant in the browser, not in the replay.** The replay fires all 17 queries at once on separate sessions; the dropdown scans (~0.2–0.6 s each) run fully in parallel with the main chart. In the browser the 10M-row dropdown scans add ~0.8 s; likely reason (not verified): the dashboard backend does not run all queries of a page fully in parallel, so they compete with the chart query. (With n=3 this was within noise.) |
| 6 Lakehouse//RT | −83% (2.16 → 0.36, t=−13) | −67% (2.94 → 0.96, t=−12) | Largest single gain. Also on the unoptimized baseline: replay 7.70 → 2.61 s (−66%). |

### Single-query checks (no cache possible – unique query text / never-seen parameter combinations), mean ± std

| Query | PRO warehouse | Lakehouse//RT | RT speed-up |
|---|---:|---:|---:|
| Baseline main chart, default parameters (star schema, 10M rows), n=3 | 2.56 ± 0.01 s | 0.89 ± 0.69 s (0.50 / 0.49 after a 1.69 s first run) | 2.9x (5.1x excl. first run) |
| Baseline main chart, 5 filtered parameter combinations | 1.36 ± 0.08 s | 0.30 ± 0.03 s | 4.5x |
| Materialized grain + metric view, 5 filtered combinations | 1.22 ± 0.39 s | 0.29 ± 0.04 s | 4.2x |
| **Full baseline landing page (28 concurrent queries, n=10)** | 7.70 ± 0.54 s | 2.61 ± 0.41 s | 3.0x |

On a warm warehouse RT is ~4.5–5x faster per query. Under concurrency the advantage shrinks to ~3x: 28 concurrent
queries on one Small RT cluster take ~5.2x the single-query time (PRO: ~3.0x). **Fewer queries per page matters on RT too.**

## 3. Key findings (n=10)

1. **First load = number of queries × cost per query, amplified by queueing on the warehouse.** The biggest
   "design" levers are pre-joining (−39% replay / −46% browser) and fewer widgets on the landing page
   (−45% / −25%). Together with Lakehouse//RT the landing page goes from 9.4 s to 1.0 s cold in the browser (−90%).
2. **Lakehouse//RT is the most effective single lever** – even without any modelling change (baseline on RT: −66%
   replay). Combined with the optimized design: 0.36 s for all 17 landing-page queries.
3. **Metric views with parameters cost ~10% (replay and browser, not significant)** in this LOD-heavy design. Use them
   for governance and reuse (Genie, multiple dashboards), not for speed.
4. **The materialized grain speeds up the chart queries (−25% replay), but in the browser most of it is hidden behind
   the filter-dropdown queries (−10%, borderline).** Pack size / loyalty group are customer attributes outside the grain;
   when used, the metric view falls back to the detail table (same results, verified in SQL and in the dashboard).
5. **"Ignored filters" (dropdowns from tiny dims) saves ~0.8 s (−21%) in the browser** – significant with n=10, but
   not visible in the replay where all queries run fully in parallel. Cheap to do, so worth it.
6. **Subsequent loads are ~1.9–2.6 s in the browser for every step** – ~1.6–1.9 s of that is loading the dashboard app
   before the first query is sent; with the dashboard cache the data arrives in 0.2–0.6 s. The optimizations matter for
   **first loads and every filter change**, because new parameter values are cold queries.

## 4. Verification performed

* **Results identical across all steps** for default parameters, pack-size fallback, product type + year + 4-star scale
  (only 6th-decimal rounding differences). Delta charts checked by hand (previous period, previous year, delta to total;
  first year NULL).
* **Browser cold runs checked in `system.query.history`:** steps 0–4 and 6 – all queries executed, 0 from cache. Step 5,
  run 1 (1.96 s) had 4 of 17 queries served from cache because the invalidation script missed `dim_brand`, `dim_product`
  and `dim_pack_size` → run excluded, script fixed (now all 9 tables), all steps re-run once more.
* **Dashboard functions tested in the browser (step 5):** single-select parameter (Time Breakdown → Year), multi-select
  parameter (Country Group → DACH), Split → Pack Size (fallback branch), dropdown values from dims, Deep Dive page renders
  all 11 charts without errors.

## 5. Caveats / known limitations

* **Deep Dive page (steps 4–6) has its own page-level filters** – selections made on the Overview do **not** carry over
  (verified). For production you would use global filters or accept separate selections. That does not affect the
  landing-page measurement.
* 10 runs per cell (see section 1 for how they were collected). Standard deviations in the browser are up to ±1.1 s
  (first load) and ±0.7 s (subsequent load); with n=10, differences of ~0.5 s are detectable (Welch t in section 2).
* Runs 4–10 of the browser cold loads: `system.query.history` shows 1,140 dashboard queries on the PRO warehouse in that
  window, 0 served from the result cache. Lakehouse//RT queries do not appear in `system.query.history` (Beta), so step 6
  could not be checked that way (its 0.65–1.35 s range matches the earlier verified runs).
* "Browser first load" = Refresh after invalidating caches (new Delta versions on all tables + full MV refresh). This
  measures the query phase; opening a never-viewed dashboard adds ~1.8 s for the app shell (first visits: step 1 8.3 s,
  step 2 6.3 s, step 3 6.7 s, step 4 3.8 s, step 5 4.0 s).
* Publishing a dashboard pre-warms its cache, and the dashboard cache does **not** react to table-property commits
  (verified in the query history) – that is why Refresh was used for cold measurements.
* One Small cluster for both PRO and RT, to compare engines rather than autoscaling. With autoscaling, the many-widget
  steps (0–3) would queue less.
* Lakehouse//RT is in Beta; default auto-stop 10 min; the first query after idling is slower (2.06 s).
* Synthetic data: score trend and dip after the 5-star launch (2026-W02) mimic the original dashboard; values are not
  real business numbers.
