#!/bin/bash
# usage: lc/step.sh <next_variant> [<variant> <run> <first_s> <subsequent_s>]
#   -> records the previous measurement (if given), then invalidates the caches of the schema the next variant reads
cd "$(dirname "$0")"
next=$1; shift
[ -n "$1" ] && ./record_lc.sh "$@"
if [ "$next" = "r_nolc" ]; then ../invalidate.sh | tail -1; else ./invalidate_lc.sh | tail -1; fi
