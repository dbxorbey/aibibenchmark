"""Replay benchmark for the liquid-clustering variants - same method as ../bench.py, results go to lc/results/.

Difference to ../bench.py: warm-up = one unmeasured full page load (not only SELECT 1), so the first measured run does
not hit a cold disk cache.

Usage: python lc/bench_lc.py <variant> [--runs 10] [--warehouse pro|rt|<id>] [--check] [--append]
"""
import argparse
import json
import os
import statistics

import build_lc
import bench
import config

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--warehouse", default=None)
    ap.add_argument("--check", action="store_true", help="print the main chart result and exit")
    ap.add_argument("--append", action="store_true", help="add the new runs to an existing result file")
    a = ap.parse_args()
    v = next(x for x in build_lc.VARIANTS if x["key"] == a.variant)
    config.SCHEMA = build_lc.schema_of(v)  # bench.connect() reads config.SCHEMA at call time
    wh = config.warehouse(a.warehouse or v["warehouse"])
    queries = bench.page1_queries(v)

    if a.check:
        _, res = bench.run_page(wh, [q for q in queries if q[0] == "w_main"], cache=False)
        for r in sorted(res[0][3])[:12]:
            print(tuple(r))
        print("rows:", res[0][2], f"time {res[0][1]:.2f}s")
        return

    # warm the warehouse (not measured) with one real page load - SELECT 1 does not warm the disk cache
    bench.run_page(wh, [("warmup", "SELECT 1")], cache=False)
    bench.run_page(wh, queries, cache=False)
    first, subsequent, per_widget = [], [], {}
    for i in range(a.runs):
        t, res = bench.run_page(wh, queries, cache=False)
        first.append(t)
        for name, dt, _, _ in res:
            per_widget.setdefault(name, []).append(dt)
        print(f"run {i+1}: first load {t:.2f}s  (slowest: {max(res, key=lambda r: r[1])[0]})", flush=True)
    bench.run_page(wh, queries, cache=True)  # prime result cache
    for i in range(a.runs):
        t, _ = bench.run_page(wh, queries, cache=True)
        subsequent.append(t)
        print(f"run {i+1}: subsequent load {t:.2f}s", flush=True)

    path = os.path.join(HERE, "results", f"replay_{v['key']}_{a.warehouse or v['warehouse']}.json")
    if a.append and os.path.exists(path):
        old = json.load(open(path))
        first, subsequent = old["first_load_s"] + first, old["subsequent_load_s"] + subsequent
        for k, x in old.get("per_widget_s", {}).items():
            per_widget[k] = x + per_widget.get(k, [])
    result = {
        "variant": v["key"], "label": v["label"], "warehouse": a.warehouse or v["warehouse"], "schema": v["schema"],
        "n_queries": len(queries),
        "n_chart_queries": sum(1 for q in queries if not q[0].startswith(("flt_", "p2_flt_"))),
        "first_load_s": first, "subsequent_load_s": subsequent,
        "first_load_median_s": statistics.median(first), "subsequent_load_median_s": statistics.median(subsequent),
        "first_load_mean_s": statistics.mean(first), "subsequent_load_mean_s": statistics.mean(subsequent),
        "first_load_stdev_s": statistics.stdev(first), "subsequent_load_stdev_s": statistics.stdev(subsequent),
        "per_widget_median_s": {k: statistics.median(x) for k, x in per_widget.items()},
        "per_widget_s": per_widget,
    }
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump(result, open(path, "w"), indent=1)
    print(json.dumps({k: result[k] for k in ("variant", "n_queries", "first_load_median_s", "subsequent_load_median_s")}))


if __name__ == "__main__":
    main()
