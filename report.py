"""Build the results table (markdown, mean ± sample std dev) from results/*.json.

Usage: python report.py  -> prints markdown, writes results/summary.md
"""
import glob
import json
import os
import statistics

import build

HERE = os.path.dirname(os.path.abspath(__file__))


def load(pattern):
    out = {}
    for f in glob.glob(os.path.join(HERE, "results", pattern)):
        r = json.load(open(f))
        out[os.path.basename(f)] = r
    return out


def main():
    replay = load("replay_*.json")
    browser = load("browser_*.json")
    def ms(x):
        return "-" if not x else f"{statistics.mean(x):.2f} ± {statistics.stdev(x):.2f}" if len(x) > 1 else f"{x[0]:.2f}"

    rows = []
    base_first = None
    for v in build.VARIANTS:
        r = replay.get(f"replay_{v['key']}_{v['warehouse']}.json")
        b = browser.get(f"browser_{v['key']}.json", {})
        if not r:
            continue
        mean_first = statistics.mean(r["first_load_s"])
        if base_first is None:
            base_first = mean_first
        rows.append((v["label"], r["n_queries"], ms(r["first_load_s"]), ms(r["subsequent_load_s"]),
                     mean_first / base_first, ms(b.get("first_load_runs_s")), ms(b.get("subsequent_load_runs_s"))))
    ref = replay.get("replay_v0_baseline_rt.json")

    md = ["| Step | Queries on page-1 load | Replay first load (s) | Replay subsequent load (s) | First load vs baseline | "
          "Browser first load (s) | Browser subsequent load (s) |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for label, n, fl, sl, rel, bf, ps in rows:
        md.append(f"| {label} | {n} | {fl} | {sl} | {rel:.0%} | {bf} | {ps} |")
    if ref:
        md.append(f"| (ref) Baseline on Lakehouse//RT | {ref['n_queries']} | {ms(ref['first_load_s'])} | "
                  f"{ms(ref['subsequent_load_s'])} | {statistics.mean(ref['first_load_s']) / base_first:.0%} | - | - |")
    text = "\n".join(md)
    open(os.path.join(HERE, "results", "summary.md"), "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
