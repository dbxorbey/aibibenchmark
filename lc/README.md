# Re-run: liquid clustering + metric view as the baseline, every lever isolated and stacked

The first run (repository root) applied the techniques cumulatively on an unclustered star schema with inline SQL.
This folder re-runs the benchmark on a new baseline: **liquid-clustered tables + a parameterized metric view on the
star schema**. Every lever is measured twice, **on its own** (isolated, vs the baseline) and **stacked** (cumulative,
vs the previous step). The metric view is no longer a separate lever; every variant queries one. Same data, same
dashboard, same warehouses and the same measurement method as the first run. n = 10 per cell.

Write-up: [`blog/blog_post.md`](blog/blog_post.md) (PDF: `blog/blog_post.pdf`), raw runs: `results/`.

## Variants

| Key | Variant | Change vs baseline |
|---|---|---|
| `l0_baseline` | Baseline | liquid-clustered star schema, metric view, 12 charts on page 1, dropdowns from the joined fact, PRO |
| `li1_prejoined` | Isolated 1 = Stacked 1 | metric view and dropdowns on the pre-joined wide table |
| `li2_matgrain` | Isolated 2 | metric view on the materialized grain, falls back to the star schema |
| `li3_fewwidgets` | Isolated 3 | only the main chart on page 1 |
| `li4_ignfilters` | Isolated 4 | dropdowns from tiny dims / static lists |
| `li5_lakehousert` | Isolated 5 | baseline on Lakehouse//RT |
| `ls2_matgrain` | Stacked 2 | stacked 1 + materialized grain (falls back to the wide table) |
| `ls3_fewwidgets` | Stacked 3 | + only the main chart on page 1 |
| `ls4_ignfilters` | Stacked 4 | + dropdowns from tiny dims |
| `ls5_lakehousert` | Stacked 5 | + Lakehouse//RT |
| `r_nolc` | Reference | baseline **without** liquid clustering (unclustered tables in `BENCH_SCHEMA`) |

Cluster keys: `fact_sales (week_id, country_id, brand_id)`, `wide_sales` and `agg_product_country_week`
`(week_idx, country_code, brand_name)`, dims on their primary key (`sql/01_clustered_tables.sql`, CTAS +
`OPTIMIZE FULL`).

## Results – browser first load (mean ± std dev, s; Welch t in brackets, |t| ≳ 2.1 = significant)

| Isolated (alone on the baseline) | Browser first | vs baseline | Replay first | vs baseline |
|---|---:|---:|---:|---:|
| Baseline (LC + metric view) | 10.31 ± 1.45 | – | 8.35 ± 0.54 | – |
| + Pre-joined wide table | 4.67 ± 0.62 | **−55%** (−11.3) | 4.55 ± 0.58 | **−45%** (−15.2) |
| + Materialized grain | 8.03 ± 0.77 | **−22%** (−4.4) | 6.07 ± 0.42 | **−27%** (−10.6) |
| + Fewer widgets on page 1 | 8.24 ± 0.54 | **−20%** (−4.2) | 6.06 ± 1.06 | **−27%** (−6.1) |
| + Dropdowns from small tables | 7.93 ± 0.58 | **−23%** (−4.8) | 7.79 ± 0.54 | **−7%** (−2.3) |
| Baseline on Lakehouse//RT | 3.55 ± 0.17 | **−66%** (−14.7) | 3.15 ± 0.11 | **−62%** (−29.8) |

| Stacked (cumulative) | Browser first | vs previous | Replay first | vs previous |
|---|---:|---:|---:|---:|
| 0 Baseline (LC + metric view) | 10.31 ± 1.45 | – | 8.35 ± 0.54 | – |
| 1 + Pre-joined wide table | 4.67 ± 0.62 | **−55%** (−11.3) | 4.55 ± 0.58 | **−45%** (−15.2) |
| 2 + Materialized grain | 4.84 ± 0.63 | +3% (+0.6, n.s.) | 3.81 ± 0.35 | **−16%** (−3.5) |
| 3 + Fewer widgets on page 1 | 3.91 ± 0.45 | **−19%** (−3.7) | 2.11 ± 0.53 | **−45%** (−8.4) |
| 4 + Dropdowns from small tables | 2.63 ± 0.38 | **−33%** (−6.8) | 1.95 ± 0.25 | −7% (−0.8, n.s.) |
| 5 + Lakehouse//RT | 0.96 ± 0.18 | **−63%** (−12.4) | 0.29 ± 0.01 * | **−85%** |
| **Total vs baseline** | | **−91%** | | **−96%** |

\* One of the 10 RT replay runs stalled: every query of that run, including trivial dropdown lookups, waited ~11 s at
the same moment (reproduced in a second session). Shown: the other 9 runs (0.28–0.33 s); mean of all 10: 1.39 s.

| Liquid clustering | Browser first | Replay first |
|---|---:|---:|
| Without (`r_nolc`) | 9.68 ± 1.85 | 7.79 ± 0.43 |
| With (baseline) | 10.31 ± 1.45 (+7%, n.s.) | 8.35 ± 0.54 (+7%, t=+2.6) |

Subsequent (cached) loads: 2.2–2.7 s for every variant.

**Server side** (`server_side.py`, from `system.query.history`, PRO only): no result-cache hit in any measured Refresh.
No file was pruned on the star schema (with or without clustering), because the filters are on dimension columns. On
the clustered wide table and materialized grain, 108–250 files were pruned over 9–10 page loads. The clustered fact
table is one 77 MB file (unclustered: two 60 MB files), which is the most likely reason for the small slowdown.

## Findings

1. **Liquid clustering does not help at 10M rows** (+7%; significant in the replay only). It prunes files only where
   the filters hit the cluster keys directly (denormalized tables). Expect it to matter with many files per table.
2. **Ranking of the single levers** (browser): Lakehouse//RT −66% > pre-join −55% > dropdowns from small tables −23%
   ≈ materialized grain −22% ≈ fewer widgets −20%.
3. **Stacked: 10.3 s → 0.96 s (−91%)**, in line with the first run (−90%).
4. **The materialized grain after the pre-join gives no browser gain** (+3%, n.s.; replay −16%): the 16 dropdown
   queries on the wide table dominate the page until they are fed from small tables.
5. **Dropdowns from small tables gain much more in the browser (−23% / −33%) than in the replay (−7%)**: the
   dashboard has fewer heavy requests to schedule and fetch.

## Method and caveats

* Replay (`bench_lc.py`): all landing-page queries in parallel; warm-up = one unmeasured full page load.
* Browser (`lc_measure.js`, e.g. via Chrome DevTools MCP `evaluate_script`): 10 rounds, all 11 dashboards interleaved
  round-robin; `step.sh` (cache invalidation of the right schema) before every measurement; one unrecorded warm-up load
  per dashboard before round 1. *First load* = click Refresh → last `lakeview-query` response; *subsequent load* =
  the page navigation right before it (dashboard cache).
* Navigate with the init script `performance.setResourceTimingBufferSize(10000)`; with the default 250-entry buffer
  the `lakeview-query` requests may never be recorded.
* Browser noise: the baseline was 11.5–12.7 s in 3 of 10 rounds (otherwise 8.6–10.1 s) while the warehouse-side page
  time did not rise; the runs are kept. Medians lead to the same conclusions.
* If the workspace uses an IP access list, keep the client IP stable during long runs; a blocked IP makes the SQL
  connector retry for 15 minutes before it fails.

## Running it

Prerequisite: the first run's setup (configuration, warehouses, `sql/00–04` in the repository root).

```bash
export BENCH_SCHEMA_LC=aibi_bench_lc                 # optional, default: <BENCH_SCHEMA>_lc
python lc/build_lc.py                                # lc/out/*.json + lc/sql/02_metric_views.sql
python run_sql.py lc/sql/01_clustered_tables.sql     # clustered copies + materialized grain
python run_sql.py lc/sql/02_metric_views.sql         # 4 metric views in the LC schema + 1 in BENCH_SCHEMA
python lc/bench_lc.py l0_baseline --check            # correctness: print the main chart result
python lc/deploy_lc.py                               # 11 published dashboards (ids in lc/out/dashboards.tsv)

python lc/bench_lc.py <variant> --runs 10            # replay (PRO variants one after another, RT in parallel)
lc/step.sh <variant> [<prev_variant> <run> <first_s> <subsequent_s>]   # browser: record previous + invalidate
python lc/report_lc.py                               # lc/results/summary.md
python lc/server_side.py --since <UTC start of round 1>
python lc/chart_lc.py && python lc/blog_pdf_lc.py    # charts + blog PDF
```

Cleanup: drop `BENCH_SCHEMA_LC` and trash the dashboards in `<dashboard folder>/lc`.
