"""Tuning the monitoring configuration from traces: Pareto front and selection.

Problem: the cheapest monitoring configuration with P(theta) <= alpha and
D <= D_max, where P(theta) is the share of time (over machines) with deficit above
theta, and D the accumulated deficit. Cost is the number of machine samples per
machine-hour. A single scalar criterion would need subjective weights, so the
result is shown as a Pareto front and one point is selected under the constraints.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np

from .integral import deficit
from .replay import Controller, simulate
from .trace import Trace


def sweep(
    trace: Trace,
    intervals: Iterable[float],
    theta: float = 64.0,
    controller: Controller | None = None,
) -> list[dict[str, Any]]:
    """Replay every polling interval on the trace and return one row per interval.

    Each row: ``interval_s``, ``cost`` (samples per machine-hour), ``P_pct``,
    ``D_GiBs``, ``balloon_GiB``, ``n_red``.
    """
    hours = trace.n_vm * trace.T / 3600.0
    rows: list[dict[str, Any]] = []
    for interval in intervals:
        run = simulate(trace, interval, controller)
        f = deficit(trace.d, run.alloc)
        rows.append(
            {
                "interval_s": float(interval),
                "cost": run.vm_samples / hours,
                "P_pct": 100.0 * float(np.mean(f > theta)),
                "D_GiBs": float(np.sum(f) * trace.dt) / 1024.0,
                "balloon_GiB": run.balloon_volume / 1024.0,
                "n_red": run.n_red,
            }
        )
    return rows


def pareto_front(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> list[dict[str, Any]]:
    """Rows not dominated by another row; all keys are minimised.

    Examples
    --------
    >>> rows = [{"n": 10, "D": 5.0}, {"n": 5, "D": 9.0}, {"n": 12, "D": 6.0}]
    >>> [(r["n"], r["D"]) for r in pareto_front(rows, ["n", "D"])]
    [(10, 5.0), (5, 9.0)]
    """

    def dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
        return all(a[k] <= b[k] for k in keys) and any(a[k] < b[k] for k in keys)

    return [dict(r) for r in rows if not any(dominates(o, r) for o in rows if o is not r)]


def select(
    rows: Sequence[Mapping[str, Any]],
    constraints: Mapping[str, float],
    objective: str,
    maximize: bool = False,
) -> dict[str, Any] | None:
    """Best row by ``objective`` among those with ``key <= value`` for all constraints.

    Returns None if no row satisfies the constraints.

    Examples
    --------
    >>> rows = [{"cost": 10, "D": 5.0}, {"cost": 5, "D": 9.0}]
    >>> select(rows, {"D": 10.0}, "cost")
    {'cost': 5, 'D': 9.0}
    >>> select(rows, {"D": 1.0}, "cost") is None
    True
    """
    ok = [r for r in rows if all(r[k] <= v for k, v in constraints.items())]
    if not ok:
        return None
    chosen = (
        max(ok, key=lambda r: r[objective]) if maximize else min(ok, key=lambda r: r[objective])
    )
    return dict(chosen)
