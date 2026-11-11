import math

import numpy as np
import pytest

from sydost_tracekit import (
    Constants,
    deficit_integral,
    estimate_constants,
    estimate_from_samples,
    hold_error_bound,
    hold_error_bounds_refined,
    linear_error_bound,
    plan_sampling,
    required_step,
    synthetic_trace,
)
from sydost_tracekit.bounds import Plan


def _random_walk_case(rng, n=20000, dt=0.01):
    d = np.cumsum(rng.normal(0, 5, size=(2, n)), axis=1) + 1000.0
    a = np.full_like(d, 1000.0)
    return d, a, dt


def test_statement_4_1_holds_on_random_signals(rng):
    for _ in range(10):
        d, a, dt = _random_walk_case(rng)
        D = deficit_integral(d, a, dt)
        for k in (10, 50, 200):
            est = estimate_from_samples(np.arange(0, d.shape[1], k) * dt, d[:, ::k], a, dt, "hold")
            assert abs(est - D) <= hold_error_bound(d, k * dt) + 1e-6


def test_refined_bounds_are_valid_and_tighter(rng):
    for _ in range(10):
        d, a, dt = _random_walk_case(rng)
        D = deficit_integral(d, a, dt)
        for k in (10, 50, 200):
            ell = k * dt
            lo, hi = hold_error_bounds_refined(d, a, dt, ell)
            est = estimate_from_samples(np.arange(0, d.shape[1], k) * dt, d[:, ::k], a, dt, "hold")
            assert lo - 1e-6 <= est - D <= hi + 1e-6
            assert hi - lo <= hold_error_bound(d, ell) + 1e-6


def test_refined_bound_is_much_tighter_below_the_allocation():
    # demand below the allocation most of the time: the refined bound sees no deficit
    dt = 0.01
    t = np.arange(0, 200.0, dt)
    d = (100.0 + 500.0 * (np.sin(2 * np.pi * t / 20.0) > 0.9))[None, :]
    a = np.full_like(d, 1000.0)
    lo, hi = hold_error_bounds_refined(d, a, dt, 1.0)
    assert lo == 0.0 and hi == 0.0
    assert hold_error_bound(d, 1.0) > 0.0


def test_refined_bounds_require_matching_shapes():
    with pytest.raises(ValueError):
        hold_error_bounds_refined(np.zeros((1, 4)), np.zeros((1, 3)), 1.0, 1.0)


def test_refined_bound_on_synthetic_scenario_is_valid():
    tr = synthetic_trace("A", T=300.0, dt=0.05, seed=7)
    a = np.full_like(tr.d, np.percentile(tr.d, 90))
    D = deficit_integral(tr.d, a, tr.dt)
    k = 20
    est = estimate_from_samples(tr.t[::k], tr.d[:, ::k], a, tr.dt, "hold")
    lo, hi = hold_error_bounds_refined(tr.d, a, tr.dt, k * tr.dt)
    assert lo - 1e-6 <= est - D <= hi + 1e-6


def test_linear_bound_formula_and_second_order():
    assert linear_error_bound(0.5, 10.0, 1.2, 0, 3.0) == pytest.approx(0.25)
    assert linear_error_bound(1.0, 10.0, 0.0, 2, 3.0) == pytest.approx(2.0)


def test_estimate_constants_of_a_linear_ramp():
    c = estimate_constants(np.array([[0.0, 1.0, 2.0, 3.0]]), 1.0)
    assert (c.V, c.L, c.M, c.K) == (3.0, 1.0, 0.0, 0)
    assert c.linear_C == 0.0


def test_estimate_constants_counts_kinks():
    d = np.array([[0.0, 1.0, 2.0, 2.0, 2.0, 3.0]])  # slope changes at two points
    c = estimate_constants(d, 1.0, kink_tol=0.5)
    assert c.K == 2 and c.L == 1.0
    assert c.linear_C == pytest.approx(6 * 1.0 / 12 + 2 * 1.0 / 3)  # T M / 12 + K L / 3
    assert estimate_constants(d, 1.0).K >= 1  # default tolerance


def test_estimate_constants_needs_three_points():
    with pytest.raises(ValueError):
        estimate_constants(np.array([[0.0, 1.0]]), 1.0)


def test_required_step_and_plan():
    c = Constants(V=100.0, L=1.0, M=0.0, K=0, linear_C=0.0)
    assert required_step(50.0, "hold", c) == pytest.approx(0.5)
    assert required_step(50.0, "linear", c) == math.inf
    c2 = Constants(V=100.0, L=1.0, M=0.0, K=0, linear_C=400.0)
    assert required_step(40.0, "linear", c2) == pytest.approx(math.sqrt(0.1))
    assert required_step(40.0, "hold", Constants(0.0, 0.0, 0.0, 0, 0.0)) == math.inf
    assert required_step(40.0, "linear", Constants(0.0, 0.0, 0.0, 0, 0.0)) == math.inf
    with pytest.raises(ValueError):
        required_step(-1.0, "hold", c)
    with pytest.raises(ValueError):
        required_step(1.0, "cubic", c)


def test_plan_sampling_picks_the_larger_admissible_step():
    c = Constants(V=100.0, L=1.0, M=0.0, K=0, linear_C=400.0)
    plan = plan_sampling(40.0, c)  # hold step 0.4 beats linear step sqrt(0.1) = 0.316
    assert isinstance(plan, Plan) and plan.method == "hold"
    assert plan.step_s == pytest.approx(0.4)
    assert plan.rate_hz == pytest.approx(2.5)
    assert plan.bound_MiBs == pytest.approx(40.0)
    c_lin = Constants(V=1000.0, L=1.0, M=0.0, K=0, linear_C=400.0)
    lin = plan_sampling(40.0, c_lin)  # hold step 0.04 loses to linear step 0.316
    assert lin.method == "linear" and lin.step_s == pytest.approx(math.sqrt(0.1))
    # no curvature and no kinks: the linear bound is zero at any step (infinite step)
    exact = plan_sampling(50.0, Constants(V=100.0, L=1.0, M=0.0, K=0, linear_C=0.0))
    assert exact.method == "linear" and math.isinf(exact.step_s) and exact.rate_hz == 0.0
    no_linear = plan_sampling(50.0, Constants(V=100.0, L=1.0, M=0.0, K=0, linear_C=1e9))
    assert no_linear.method == "hold" and no_linear.step_s == pytest.approx(0.5)
    flat = plan_sampling(1.0, Constants(0.0, 0.0, 0.0, 0, 0.0))
    assert flat.rate_hz == 0.0 and flat.bound_MiBs == 0.0
