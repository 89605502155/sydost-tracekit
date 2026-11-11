"""Accumulated deficit: its integral, its estimate from samples, and exact formulas.

Theory (Halmos, sections 23-27). The samples held for a step l define a simple
function d_l. The estimate D_l = integral of (d_l - a)^+ is the integral of a
simple function. As l -> 0, d_l -> d almost everywhere and the Lebesgue
dominated convergence theorem gives D_l -> D. The allocation a is known from the
host journal; the error comes only from the reconstruction of d.

Exact integral of the positive part of a piecewise linear signal: on each
segment the difference g = x - a is linear, so its positive part is found from
the crossing point (see :func:`positive_part_integral`).
"""

from __future__ import annotations

import numpy as np

from .reconstruct import METHODS
from .trace import Trace


def deficit(d: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Instantaneous deficit f = (d - a)^+, MiB.

    Examples
    --------
    >>> deficit(np.array([3.0, 1.0]), np.array([2.0, 2.0])).tolist()
    [1.0, 0.0]
    """
    return np.asarray(np.maximum(np.asarray(d, float) - np.asarray(a, float), 0.0), dtype=float)


def deficit_integral(d: np.ndarray, a: np.ndarray, dt: float) -> float:
    """Accumulated deficit D = integral of (d - a)^+ over time, summed over machines, MiB*s.

    Examples
    --------
    >>> deficit_integral(np.array([[3.0, 3.0]]), np.array([[2.0, 2.0]]), 0.5)
    1.0
    """
    return float(np.sum(deficit(d, a)) * dt)


def total_variation(x: np.ndarray) -> float:
    """Total variation of the series along the last axis, summed over rows.

    Examples
    --------
    >>> total_variation(np.array([0.0, 2.0, 1.0, 4.0]))
    6.0
    """
    return float(np.abs(np.diff(np.atleast_2d(x), axis=-1)).sum())


def positive_part_integral(t: np.ndarray, x: np.ndarray, a: np.ndarray) -> float:
    """Exact integral of (x - a)^+ for piecewise linear x and a on the knots t.

    The integral of the positive part of the difference g = x - a over each
    segment is computed in closed form from the crossing point of g with zero.
    A step allocation is written with a repeated knot (a zero-length segment).

    Parameters
    ----------
    t : array of shape (m,)
        Increasing knot times, s.
    x, a : arrays of shape (m,)
        Values of the demand and of the allocation at the knots, MiB.

    Examples
    --------
    >>> import numpy as np
    >>> t = np.array([0.0, 2.0])
    >>> positive_part_integral(t, np.array([0.0, 4.0]), np.array([2.0, 2.0]))
    1.0
    """
    t = np.asarray(t, float)
    g = np.asarray(x, float) - np.asarray(a, float)
    if t.ndim != 1 or t.size != g.size or t.size < 2:
        raise ValueError("t, x and a must be 1-D arrays of the same length >= 2")
    if np.any(np.diff(t) < 0):
        raise ValueError("knot times must not decrease")
    g0, g1 = g[:-1], g[1:]
    h = np.diff(t)
    both_pos = (g0 >= 0) & (g1 >= 0)
    down = (g0 > 0) & (g1 < 0)  # crosses zero going down
    up = (g0 < 0) & (g1 > 0)  # crosses zero going up
    area = np.where(both_pos, (g0 + g1) / 2.0 * h, 0.0)
    den_down = np.where(down, g0 - g1, 1.0)
    area = np.where(down, g0 * g0 * h / (2.0 * den_down), area)
    den_up = np.where(up, g1 - g0, 1.0)
    area = np.where(up, g1 * g1 * h / (2.0 * den_up), area)
    return float(area.sum())


def estimate_from_samples(
    t_s: np.ndarray, d_s: np.ndarray, a_grid: np.ndarray, dt: float, method: str = "linear"
) -> float:
    """Estimate of D from the samples d_s at the times t_s, with a known on a grid of step dt.

    Parameters
    ----------
    t_s : array (m,)
        Sample times, s, on the grid of ``a_grid``.
    d_s : array (n_vm, m)
        Samples of the demand.
    a_grid : array (n_vm, n)
        Allocation on the grid of step dt.
    dt : float
        Grid step, s.
    method : str
        ``"hold"`` or ``"linear"``.
    """
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}")
    a_grid = np.atleast_2d(a_grid)
    t_grid = np.arange(a_grid.shape[1]) * dt
    d_s = np.atleast_2d(d_s)
    rec = np.vstack([METHODS[method](t_s, row, t_grid) for row in d_s])
    return deficit_integral(rec, a_grid, dt)


def sampling_study(
    trace: Trace,
    alloc: np.ndarray,
    steps: list[float],
    methods: tuple[str, ...] = ("hold", "linear"),
) -> list[dict[str, float]]:
    """Relative errors of the estimate from samples with step l, against the exact D.

    ``trace`` is the reference with a fine step (it is taken as exact); ``alloc``
    is the allocation on the same grid. Steps are rounded to multiples of the
    grid step.

    Examples
    --------
    >>> import numpy as np
    >>> tr = Trace(0.1, np.linspace(0.0, 10.0, 101)[None, :], ["vm1"])
    >>> rows = sampling_study(tr, np.full((1, 101), 4.0), [0.2], methods=("linear",))
    >>> abs(rows[0]["linear_rel_pct"]) < 1e-9
    True
    """
    a = np.atleast_2d(np.asarray(alloc, float))
    truth = deficit_integral(trace.d, a, trace.dt)
    rows: list[dict[str, float]] = []
    for ell in steps:
        k = max(1, round(ell / trace.dt))
        t_s = trace.t[::k]
        row: dict[str, float] = {"step_s": k * trace.dt, "D_true_MiBs": truth}
        for method in methods:
            est = estimate_from_samples(t_s, trace.d[:, ::k], a, trace.dt, method)
            row[f"{method}_MiBs"] = est
            row[f"{method}_rel_pct"] = 100.0 * (est / truth - 1.0) if truth > 0 else 0.0
        rows.append(row)
    return rows
