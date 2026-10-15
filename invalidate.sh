#!/bin/bash
# usage: ./invalidate.sh  -> new Delta versions on all tables + FULL refresh of the materialized view, so that no
# result cache (SQL warehouse or dashboard) can be reused. Runs on BENCH_WAREHOUSE_SETUP (not the bench warehouses).
cd "$(dirname "$0")"
"${PYTHON:-python}" run_sql.py sql/90_invalidate_caches.sql --warehouse setup
