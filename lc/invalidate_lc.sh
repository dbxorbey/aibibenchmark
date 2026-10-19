#!/bin/bash
# usage: lc/invalidate_lc.sh  -> new Delta versions on all tables + FULL refresh of the materialized view in
# BENCH_SCHEMA_LC (the reference r_nolc uses ../invalidate.sh). Runs on BENCH_WAREHOUSE_SETUP.
cd "$(dirname "$0")"
"${PYTHON:-python}" ../run_sql.py sql/90_invalidate_caches.sql --warehouse setup
