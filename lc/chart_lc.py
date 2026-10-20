"""Bar charts of the liquid-clustering re-run (browser first load): isolated and stacked, % always vs the baseline.

Same style as ../chart.py (reuses its page template and SVG export).

Usage: python lc/chart_lc.py  -> writes blog/{isolated,stacked}_chart.{html,svg}
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import chart  # noqa: E402

BASE = ("l0_baseline", "Baseline", "LC + metric view")
# isolated: baseline first, then from the smallest to the largest single gain
ISOLATED = [BASE, ("li3_fewwidgets", "+ Lean", "landing page"), ("li2_matgrain", "+ Materialized", "aggregate"),
            ("li4_ignfilters", "+ Dropdowns from", "small tables"), ("li1_prejoined", "+ Pre-joined", "wide table"),
            ("li5_lakehousert", "+ Lakehouse//RT", "warehouse")]
STACKED = [BASE, ("li1_prejoined", "+ Pre-joined", "wide table"), ("ls2_matgrain", "+ Materialized", "aggregate"),
           ("ls3_fewwidgets", "+ Lean", "landing page"), ("ls4_ignfilters", "+ Dropdowns from", "small tables"),
           ("ls5_lakehousert", "+ Lakehouse//RT", "warehouse")]


def runs(k):
    return json.load(open(os.path.join(HERE, "results", f"browser_{k}.json")))["first_load_runs_s"]


def write(name, bars, page):
    steps = [{"l1": l1, "l2": l2, "runs": runs(k)} for k, l1, l2 in bars]
    out = os.path.join(HERE, "blog", f"{name}_chart.html")
    open(out, "w").write(page.replace("__DATA__", json.dumps({"steps": steps})))
    chart.write_svg(out, os.path.join(HERE, "blog", f"{name}_chart.svg"))


def main():
    os.makedirs(os.path.join(HERE, "blog"), exist_ok=True)
    first, last = (sum(runs(k)) / len(runs(k)) for k in (STACKED[0][0], STACKED[-1][0]))
    write("isolated", ISOLATED, chart.PAGE
          .replace("Cold landing-page load per optimization step", "Cold landing-page load, each measure on its own")
          .replace("const p = mean(rows[i - 1].runs);", "const p = mean(rows[0].runs);")
          .replace("'Browser first load per cumulative step, descending from 9.4 s to 1.0 s'",
                   "'Browser first load of the baseline and of each measure applied alone to the baseline'"))
    write("stacked", STACKED, chart.PAGE
          .replace("const p = mean(rows[i - 1].runs);", "const p = mean(rows[0].runs);")
          .replace("descending from 9.4 s to 1.0 s", f"descending from {first:.1f} s to {last:.1f} s"))


if __name__ == "__main__":
    main()
