"""Cold check: main-chart query with parameter combinations that never ran before (no cache can hit)."""
import json, statistics, sys, time, uuid
import build, bench, config

combos = [
    {"p_time": "Week", "f_country": ["DE", "AT"]},
    {"p_time": "Month", "p_split": "Product Type", "f_year": ["2025"]},
    {"p_scale": "4-star", "f_country_group": ["Nordics", "UK"], "p_weeks": "Include all weeks"},
    {"p_split": "Brand", "f_brand": [], "f_new_repeat": ["New"]},
    {"p_time": "Year", "f_product_type": ["Premium", "Accessory"], "f_quarter": ["2024-Q3", "2025-Q3", "2026-Q3"]},
]
out = {}
for key, wh in [("v0_baseline", "pro"), ("v0_baseline", "rt"), ("v3_matgrain", "pro"), ("v6_lakehousert", "rt")]:
    v = next(x for x in build.VARIANTS if x["key"] == key)
    times = []
    for c in combos:
        c = dict(c)
        # a never-seen value in an otherwise empty multi-select keeps results identical but makes the query text unique
        c.setdefault("f_week", [])
        q = [s for n, s in bench.page1_queries(v, c) if n == "w_main"][0]
        q = q.replace("ORDER BY period, split_value", f"ORDER BY period, split_value /* {uuid.uuid4()} */")
        with bench.connect(config.warehouse(wh), False) as conn, conn.cursor() as cur:
            t0 = time.perf_counter(); cur.execute(q); cur.fetchall(); times.append(time.perf_counter() - t0)
    out[f"{key}@{wh}"] = {"times": times, "median_s": statistics.median(times)}
    print(key, wh, [round(t, 2) for t in times], "median", round(statistics.median(times), 2), flush=True)
json.dump(out, open("results/cold_unique_main_chart.json", "w"), indent=1)
