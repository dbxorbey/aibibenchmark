"""Re-run on a new baseline: liquid-clustered tables + parameterized metric view on the star schema.

All variants read schema BENCH_SCHEMA_LC (liquid-clustered copies of BENCH_SCHEMA, see sql/01_clustered_tables.sql),
except the reference r_nolc, which reads the unclustered tables in BENCH_SCHEMA. Reuses the SQL templates of
../build.py unchanged and adds the source "agg_star" (materialized grain with fallback to the star schema, so the
isolated mat-grain variant does not include the pre-join). Every variant queries a metric view.

  l0_baseline     liquid clustering + metric view on the star schema, 12 charts on page 1, dropdowns from joined fact, PRO
Isolated (each measure alone on l0):
  li1_prejoined   metric view on the pre-joined wide table, dropdowns from the wide table      (= stacked step 1)
  li2_matgrain    metric view on the materialized grain, fallback to the star schema
  li3_fewwidgets  only the main chart on page 1
  li4_ignfilters  dropdown values from tiny dims / static lists
  li5_lakehousert l0 on the Lakehouse//RT warehouse
Stacked (cumulative, starting from l0 -> li1):
  ls2_matgrain    + materialized grain (fallback to the wide table)
  ls3_fewwidgets  + only the main chart on page 1
  ls4_ignfilters  + dropdown values from tiny dims
  ls5_lakehousert + Lakehouse//RT
Reference:
  r_nolc          l0 without liquid clustering (metric view on the unclustered star schema in BENCH_SCHEMA)

Usage: python lc/build_lc.py   -> writes lc/out/<variant>.json, lc/out/<variant>_replay.json, lc/sql/02_metric_views.sql
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import build  # noqa: E402
import config  # noqa: E402

_orig_product_lod = build.product_lod
_orig_filter_value_datasets = build.filter_value_datasets


def product_lod(x, source):
    if source != "agg_star":
        return _orig_product_lod(x, source)
    # both branches are guarded by constant predicates -> the optimizer prunes the unused one
    return (f"SELECT * FROM ({build.agg_product_lod(x)}) WHERE {build.use_agg_pred(x)}\n"
            f"  UNION ALL\n"
            f"  SELECT * FROM ({build.detail_product_lod(x, 'star')}) WHERE NOT {build.use_agg_pred(x)}")


def filter_value_datasets(variant):
    # dropdowns of the isolated mat-grain variant come from the joined star fact, like the baseline
    if variant["source"] == "agg_star":
        variant = dict(variant, source="star")
    return _orig_filter_value_datasets(variant)


build.product_lod = product_lod
build.filter_value_datasets = filter_value_datasets


def schema_of(variant):
    return config.SCHEMA_LC if variant["schema"] == "lc" else config.SCHEMA


BASE = {"mode": "mv", "source": "star", "metric_view": "mv_sales_performance_star", "page1_all": True,
        "filter_values": "fact", "warehouse": "pro", "schema": "lc"}
PREJ = {**BASE, "source": "wide", "metric_view": "mv_sales_performance"}
STK2 = {**PREJ, "source": "agg", "metric_view": "mv_sales_performance_agg"}
VARIANTS = [
    {**BASE, "key": "l0_baseline", "label": "0 - Baseline (liquid clustering + metric view on star schema)",
     "desc": "Liquid-clustered fact + 6 dims; datasets query a parameterized metric view on the star schema; "
             "12 charts on page 1."},
    {**PREJ, "key": "li1_prejoined", "label": "Isolated 1 / Stacked 1 - + pre-joined wide table",
     "desc": "Baseline, but the metric view (and the dropdowns) read one denormalized table (no joins)."},
    {**BASE, "key": "li2_matgrain", "label": "Isolated 2 - + materialized grain",
     "source": "agg_star", "metric_view": "mv_sales_performance_agg_star",
     "desc": "Baseline, but the metric view reads the materialized product x country x week grain (falls back to the "
             "star schema for pack size / loyalty)."},
    {**BASE, "key": "li3_fewwidgets", "label": "Isolated 3 - + fewer widgets on page 1", "page1_all": False,
     "desc": "Baseline, but only the main chart on the landing page; the 11 secondary charts move to 'Deep Dive'."},
    {**BASE, "key": "li4_ignfilters", "label": "Isolated 4 - + ignored filters", "filter_values": "dims",
     "desc": "Baseline, but filter dropdowns read tiny dim tables / static lists instead of the joined 10M-row fact."},
    {**BASE, "key": "li5_lakehousert", "label": "Isolated 5 - Baseline on Lakehouse//RT", "warehouse": "rt",
     "desc": "Baseline dashboard unchanged, executed on a Lakehouse//RT (Real-Time) warehouse."},
    {**STK2, "key": "ls2_matgrain", "label": "Stacked 2 - + materialized grain",
     "desc": "Pre-joined + metric view routes to the materialized grain (falls back to the wide table)."},
    {**STK2, "key": "ls3_fewwidgets", "label": "Stacked 3 - + fewer widgets on page 1", "page1_all": False,
     "desc": "Stacked 2 + only the main chart on the landing page; 11 secondary charts on 'Deep Dive'."},
    {**STK2, "key": "ls4_ignfilters", "label": "Stacked 4 - + ignored filters", "page1_all": False,
     "filter_values": "dims", "desc": "Stacked 3 + filter dropdowns from tiny dims / static lists."},
    {**STK2, "key": "ls5_lakehousert", "label": "Stacked 5 - + Lakehouse//RT", "page1_all": False,
     "filter_values": "dims", "warehouse": "rt", "desc": "Stacked 4, executed on a Lakehouse//RT warehouse."},
    {**BASE, "key": "r_nolc", "label": "Reference - baseline without liquid clustering", "schema": "base",
     "desc": "Parameterized metric view on the unclustered star schema."},
]
ISOLATED = ["l0_baseline", "li1_prejoined", "li2_matgrain", "li3_fewwidgets", "li4_ignfilters", "li5_lakehousert"]
STACKED = ["l0_baseline", "li1_prejoined", "ls2_matgrain", "ls3_fewwidgets", "ls4_ignfilters", "ls5_lakehousert"]
# (name, source, schema placeholder)
METRIC_VIEWS = [("mv_sales_performance_star", "star", "schema_lc"), ("mv_sales_performance", "wide", "schema_lc"),
                ("mv_sales_performance_agg", "agg", "schema_lc"), ("mv_sales_performance_agg_star", "agg_star", "schema_lc"),
                ("mv_sales_performance_star", "star", "schema")]

if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "sql", "02_metric_views.sql"), "w") as f:
        f.write("-- Generated by lc/build_lc.py\n")
        for name, source, sch in METRIC_VIEWS:
            build.FQ = "${catalog}.${" + sch + "}"  # metric-view DDL uses fully qualified names
            f.write(build.metric_view_ddl(name, source))
    for v in VARIANTS:
        dash, replay = build.build_dashboard(v)
        json.dump(dash, open(os.path.join(HERE, "out", f"{v['key']}.json"), "w"), indent=1)
        json.dump(replay, open(os.path.join(HERE, "out", f"{v['key']}_replay.json"), "w"), indent=1)
        print(v["key"], "datasets:", len(dash["datasets"]), "pages:", len(dash["pages"]))
