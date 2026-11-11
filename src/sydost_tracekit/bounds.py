"""A-priori and refined error bounds of the accumulated-deficit estimate.

Statement 4.1 (hold). |D_l - D| <= l * V(d), where V is the total variation of
the demand. It follows from |x^+ - y^+| <= |x - y|. It is valid, but loose: the
bound counts variation at all times, also when the demand stays below the
allocation.

Refined hold bound (this package). The error of a sample at time t_j on the
step [t_j, t_j + l) is nonzero only where the demand or the held value exceeds
the allocation. Therefore, on the fine grid of the reference trace,

    -sum dt (d_k - x_j)^+ 1{d_k > a_k}  <=  D_l - D  <=  sum dt (x_j - d_k)^+ 1{x_j > a_k},

where x_j = d(t_j) is the held value of the fine point k. The sharper form used
in the code is the pointwise one: the error of a point is at least
-(d_k - max(x_j, a_k))^+ and at most (x_j - max(d_k, a_k))^+. The lower bound
counts only the rises of the demand above the allocation, the upper bound only
the falls of the held value above it. Both are computed from the reference trace
and the allocation, which are known.

Statement 4.2 (linear, second order). If d is L-Lipschitz with K kinks and
|d''| <= M away from the kinks, then |D_lin - D| <= l^2 (T M / 12 + K L / 3).
The constants are estimated from a reference trace by :func:`estimate_constants`;
for noisy traces M and K are large and the bound is loose. The bound is a
proof-sketch statement; see docs/en/bounds.md for the derivation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .integral import total_variation


def hold_error_bound(d_fine: np.ndarray, ell: float) -> float:
    """Statement 4.1: l * V(d), with V computed on the fine grid.

    Examples
    --------
    >>> hold_error_bound([[0.0, 2.0, 1.0]], 0.5)
    1.5
    """
    return ell * total_variation(np.asarray(d_fine, float))


def hold_error_bounds_refined(
    d: np.ndarray, a: np.ndarray, dt: float, ell: float
) -> tuple[float, float]:
    """Refined lower and upper bounds of D_l - D for the hold estimate.

    ``d`` and ``a`` are on the fine grid of step ``dt``; ``ell`` is a multiple of
    ``dt`` (rounded). Returns ``(lower, upper)`` with lower <= D_l - D <= upper.

    Examples
    --------
    >>> d = np.array([[0.0, 4.0, 0.0, 0.0]])
    >>> a = np.full((1, 4), 3.0)
    >>> hold_error_bounds_refined(d, a, 1.0, 2.0)
    (-1.0, 0.0)
    """
    d = np.atleast_2d(np.asarray(d, float))
    a = np.atleast_2d(np.asarray(a, float))
    if d.shape != a.shape:
        raise ValueError("d and a must have the same shape")
    m = max(1, round(ell / dt))
    idx = (np.arange(d.shape[1]) // m) * m
    x = d[:, idx]
    rise = np.maximum(d - np.maximum(x, a), 0.0)
    fall = np.maximum(x - np.maximum(d, a), 0.0)
    return -dt * float(rise.sum()), dt * float(fall.sum())


def linear_error_bound(ell: float, T: float, M: float, K: int, L: float) -> float:
    """Statement 4.2: l^2 (T M / 12 + K L / 3) for one machine.

    Examples
    --------
    >>> linear_error_bound(0.5, 10.0, 1.2, 0, 3.0)
    0.25
    """
    return ell * ell * (T * M / 12.0 + K * L / 3.0)


@dataclass(frozen=True)
class Constants:
    """Constants of the bounds of one trace, summed over the machines.

    V is the total variation, L and M are the largest over machines, K is the
    total number of kinks; ``linear_C`` is sum over machines of T M / 12 + K L / 3.
    """

    V: float
    L: float
    M: float
    K: int
    linear_C: float


def estimate_constants(d: np.ndarray, dt: float, kink_tol: float | None = None) -> Constants:
    """Estimate V, L, M, K of the bounds from a fine reference trace.

    A kink is a change of slope larger than ``kink_tol`` (MiB/s); by default it is
    10 % of the largest slope of the machine. M is the largest second difference
    divided by dt^2, a conservative estimate.

    Examples
    --------
    >>> import numpy as np
    >>> c = estimate_constants(np.array([[0.0, 1.0, 2.0, 3.0]]), 1.0)
    >>> c.V, c.L, c.M, c.K
    (3.0, 1.0, 0.0, 0)
    """
    d = np.atleast_2d(np.asarray(d, float))
    slope = np.diff(d, axis=1) / dt
    if slope.shape[1] < 2:
        raise ValueError("the trace needs at least three points")
    second = np.diff(slope, axis=1) / dt
    V = total_variation(d)
    L = float(np.max(np.abs(slope)))
    M = float(np.max(np.abs(second)))
    K = 0
    linear_C = 0.0
    T = d.shape[1] * dt
    for i in range(d.shape[0]):
        Li = float(np.max(np.abs(slope[i])))
        tol = kink_tol if kink_tol is not None else 0.1 * Li
        ki = int(np.sum(np.abs(np.diff(slope[i])) > tol))
        Mi = float(np.max(np.abs(second[i])))
        K += ki
        linear_C += T * Mi / 12.0 + ki * Li / 3.0
    return Constants(V=V, L=L, M=M, K=K, linear_C=linear_C)


def required_step(target: float, method: str, c: Constants) -> float:
    """Largest step l for which the bound of ``method`` does not exceed ``target``.

    Parameters
    ----------
    target : float
        Admissible absolute error of D, MiB*s (positive).
    method : str
        ``"hold"`` (l V <= target) or ``"linear"`` (l^2 C <= target).
    c : Constants
        Constants of the trace.

    Examples
    --------
    >>> c = Constants(V=100.0, L=1.0, M=0.0, K=0, linear_C=0.0)
    >>> required_step(50.0, "hold", c)
    0.5
    """
    if target <= 0:
        raise ValueError("the target error must be positive")
    if method == "hold":
        return math.inf if c.V == 0 else target / c.V
    if method == "linear":
        return math.inf if c.linear_C == 0 else math.sqrt(target / c.linear_C)
    raise ValueError(f"unknown method {method!r}")


@dataclass(frozen=True)
class Plan:
    """Sampling plan for a target error: method, step, rate, and the bound at that step."""

    method: str
    step_s: float
    rate_hz: float
    bound_MiBs: float


def plan_sampling(target: float, c: Constants) -> Plan:
    """Choose the method that needs the fewest samples for the target error.

    The method with the largest admissible step gives the lowest rate. The step
    is the largest one for which the bound does not exceed the target. The rate
    is 1 / step, per machine.

    Examples
    --------
    >>> c = Constants(V=100.0, L=1.0, M=0.0, K=0, linear_C=1e9)
    >>> p = plan_sampling(50.0, c)
    >>> (p.method, p.step_s, p.rate_hz)
    ('hold', 0.5, 2.0)
    """
    best: Plan | None = None
    for method in ("hold", "linear"):
        step = required_step(target, method, c)
        if math.isinf(step):
            bound = 0.0
        elif method == "hold":
            bound = step * c.V
        else:
            bound = step * step * c.linear_C
        plan = Plan(method, step, 0.0 if math.isinf(step) else 1.0 / step, bound)
        if best is None or plan.step_s > best.step_s:
            best = plan
    if best is None:  # pragma: no cover - the loop always sets it
        raise RuntimeError("no sampling plan")
    return best
