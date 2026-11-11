"""HEAVY: error of the deficit estimate from samples against a fine reference.

With a synthetic reference (default) or a recorded trace (--trace):

    python3 experiments/sampling_accuracy.py --scenario A --T 1800 --dt 0.01 --out out_sampling

Expected runtime: a few minutes and about 200 MiB at the default 30 min with dt = 0.01 s.
Not run by the tests. The CSV has the error for each policy interval and sample step.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from sydost_tracekit import load_trace, sampling_study, simulate, synthetic_trace


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--trace", help="reference trace (trace format), fine step")
    ap.add_argument("--scenario", default="A")
    ap.add_argument("--T", type=float, default=1800.0)
    ap.add_argument("--dt", type=float, default=0.01)
    ap.add_argument("--policies", default="2,4,8", help="polling intervals, s")
    ap.add_argument("--steps", default="0.05,0.1,0.2,0.5,1,2", help="sample steps, s")
    ap.add_argument("--out", default="out_sampling")
    args = ap.parse_args()
    truth = (
        load_trace(args.trace)
        if args.trace
        else synthetic_trace(args.scenario, T=args.T, dt=args.dt, seed=7)
    )
    steps = [float(x) for x in args.steps.split(",")]
    rows: list[dict[str, float]] = []
    for interval in (float(x) for x in args.policies.split(",")):
        run = simulate(truth, interval)
        rows.extend(
            {"policy_s": interval, **row} for row in sampling_study(truth, run.alloc, steps)
        )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "sampling.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
