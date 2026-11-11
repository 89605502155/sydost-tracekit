"""Command line: ``sydost-tracekit record | integrate | bound | tune``.

record
    Run the guest recorder on this machine (the same code as recorder.py).
integrate
    Estimate D from samples of a reference trace for several steps and methods.
bound
    Constants of a reference trace and a-priori bounds for a step or a target error.
tune
    Replay polling intervals on a trace, print the Pareto front and the selection.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import __version__
from .bounds import estimate_constants, hold_error_bound, plan_sampling
from .integral import sampling_study
from .recorder import record
from .trace import load_trace
from .tune import pareto_front, select, sweep


def _floats(text: str) -> list[float]:
    return [float(x) for x in text.split(",") if x.strip()]


def _cmd_record(args: argparse.Namespace) -> int:
    summary = record(args.out, args.hz, args.duration, args.root)
    with open(args.out + ".json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def _cmd_integrate(args: argparse.Namespace) -> int:
    ref = load_trace(args.trace)
    alloc = load_trace(args.alloc)
    if alloc.d.shape != ref.d.shape or alloc.dt != ref.dt:
        print("error: the allocation must have the grid and machines of the trace", file=sys.stderr)
        return 2
    methods = tuple(m.strip() for m in args.methods.split(","))
    rows = sampling_study(ref, alloc.d, _floats(args.steps), methods)
    print(f"D_true = {rows[0]['D_true_MiBs'] / 1024.0:.4f} GiB*s")
    header = ["step_s", *[f"{m}_rel_pct" for m in methods]]
    print("\t".join(header))
    for row in rows:
        print("\t".join(f"{row[k]:.4f}" for k in header))
    return 0


def _cmd_bound(args: argparse.Namespace) -> int:
    ref = load_trace(args.trace)
    c = estimate_constants(ref.d, ref.dt)
    print(f"V = {c.V:.3f} MiB, L = {c.L:.3f} MiB/s, M = {c.M:.3f} MiB/s^2, K = {c.K}")
    for ell in _floats(args.steps):
        print(
            f"step {ell:g} s: hold bound l*V = {hold_error_bound(ref.d, ell):.3f} MiB*s, "
            f"linear bound = {ell * ell * c.linear_C:.3f} MiB*s"
        )
    if args.target is not None:
        plan = plan_sampling(args.target, c)
        print(
            f"target {args.target:g} MiB*s: method {plan.method}, step {plan.step_s:.4g} s, "
            f"rate {plan.rate_hz:.4g} Hz per machine"
        )
    return 0


def _cmd_tune(args: argparse.Namespace) -> int:
    ref = load_trace(args.trace)
    rows = sweep(ref, _floats(args.intervals), theta=args.theta)
    keys = ["cost", "D_GiBs"]
    front = pareto_front(rows, keys)
    print("interval_s\tcost\tP_pct\tD_GiBs\tpareto")
    for r in rows:
        mark = "*" if r in front else ""
        print(f"{r['interval_s']:g}\t{r['cost']:.2f}\t{r['P_pct']:.3f}\t{r['D_GiBs']:.4f}\t{mark}")
    chosen = select(rows, {"P_pct": args.alpha, "D_GiBs": args.dmax}, "cost")
    if chosen is None:
        print("no configuration satisfies the constraints")
    else:
        print(f"selected: interval {chosen['interval_s']:g} s, cost {chosen['cost']:.2f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser of the command line."""
    ap = argparse.ArgumentParser(prog="sydost-tracekit", description=__doc__.split("\n")[0])
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("record", help="run the guest recorder")
    p.add_argument("--hz", type=float, default=10.0)
    p.add_argument("--duration", type=float, default=600.0)
    p.add_argument("--out", default="trace.csv")
    p.add_argument("--root", default="/proc")
    p.set_defaults(func=_cmd_record)

    p = sub.add_parser("integrate", help="estimate D from samples")
    p.add_argument("trace", help="reference trace (fine step)")
    p.add_argument("--alloc", required=True, help="allocation on the same grid (trace format)")
    p.add_argument("--steps", default="0.5,1,2", help="sample steps, s")
    p.add_argument("--methods", default="hold,linear")
    p.set_defaults(func=_cmd_integrate)

    p = sub.add_parser("bound", help="a-priori bounds and the sampling rate for a target")
    p.add_argument("trace", help="reference trace")
    p.add_argument("--steps", default="1", help="steps for which the bounds are printed, s")
    p.add_argument("--target", type=float, help="admissible error of D, MiB*s")
    p.set_defaults(func=_cmd_bound)

    p = sub.add_parser("tune", help="replay polling intervals and select one")
    p.add_argument("trace", help="training trace")
    p.add_argument("--intervals", default="1,2,4,8")
    p.add_argument("--theta", type=float, default=64.0, help="deficit threshold, MiB")
    p.add_argument("--alpha", type=float, default=0.5, help="admissible P(theta), %%")
    p.add_argument("--dmax", type=float, default=float("inf"), help="admissible D, GiB*s")
    p.set_defaults(func=_cmd_tune)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    args = build_parser().parse_args(argv)
    result: int = args.func(args)
    return result
