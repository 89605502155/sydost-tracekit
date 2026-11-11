"""Validation of the bounds and of the planner on held-out and randomized synthetic data.

Defaults were not chosen with these scenarios: they only check the claims over several seeds,
randomized allocations and the held-out scenario D (periodic plus bursty load).
"""

from __future__ import annotations

import numpy as np
import pytest

from sydost_tracekit import (
    deficit_integral,
    estimate_constants,
    estimate_from_samples,
    hold_error_bound,
    hold_error_bounds_refined,
    plan_sampling,
    synthetic_trace,
)
from sydost_tracekit.integral import total_variation

SEEDS = (11, 12, 13, 14)
SCENARIOS = ("A", "B", "C", "D")


def _allocations(d: np.ndarray, rng: np.random.Generator) -> list[np.ndarray]:
    """Constant allocation at a random quantile, and a random piecewise constant one."""
    n_vm, n = d.shape
    const = np.stack([np.full(n, np.quantile(row, rng.uniform(0.3, 0.9))) for row in d])
    steps = np.empty_like(d)
    for i in range(n_vm):
        knots = np.sort(rng.choice(n, size=5, replace=False))
        levels = np.quantile(d[i], rng.uniform(0.2, 0.95, size=6))
        idx = np.searchsorted(knots, np.arange(n), side="right")
        steps[i] = levels[idx]
    return [const, steps]


def _hold_estimate(d: np.ndarray, a: np.ndarray, dt: float, k: int) -> float:
    t_s = np.arange(0, d.shape[1], k) * dt
    return estimate_from_samples(t_s, d[:, ::k], a, dt, "hold")


@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("seed", SEEDS)
def test_refined_bound_and_statement_4_1_hold(scenario, seed):
    rng = np.random.default_rng(seed)
    dt = 0.1
    tr = synthetic_trace(scenario, T=300.0, dt=dt, seed=seed)
    for a in _allocations(tr.d, rng):
        truth = deficit_integral(tr.d, a, dt)
        for k in (1, 3, 10, 40, 150):
            ell = k * dt
            est = _hold_estimate(tr.d, a, dt, k)
            lo, hi = hold_error_bounds_refined(tr.d, a, dt, ell)
            tol = 1e-9 * max(1.0, abs(truth))
            assert lo - tol <= est - truth <= hi + tol
            assert hi - lo <= 2.0 * ell * total_variation(tr.d) + tol
            assert abs(est - truth) <= hold_error_bound(tr.d, ell) + tol


@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("seed", SEEDS)
def test_planner_hold_plan_meets_target_out_of_sample(scenario, seed):
    """Constants are estimated on one seed; the error is checked on another."""
    rng = np.random.default_rng(seed + 100)
    dt = 0.1
    train = synthetic_trace(scenario, T=300.0, dt=dt, seed=seed)
    test = synthetic_trace(scenario, T=300.0, dt=dt, seed=seed + 1000)
    a = _allocations(test.d, rng)[0]
    truth = deficit_integral(test.d, a, dt)
    if truth <= 0:
        pytest.skip("no deficit for this allocation")
    target = 0.02 * truth
    plan = plan_sampling(target, estimate_constants(train.d, dt))
    if plan.method == "hold":
        assert plan.bound_MiBs <= target * (1 + 1e-9)
        k = max(1, int(np.floor(plan.step_s / dt + 1e-9)))
        est = _hold_estimate(test.d, a, dt, k)
        assert abs(est - truth) <= target
