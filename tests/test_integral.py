import numpy as np
import pytest

from sydost_tracekit import (
    Trace,
    deficit,
    deficit_integral,
    estimate_from_samples,
    positive_part_integral,
    sampling_study,
    total_variation,
)


def test_deficit_and_integral():
    d = np.array([[3.0, 1.0, 5.0]])
    a = np.array([[2.0, 2.0, 2.0]])
    assert deficit(d, a).tolist() == [[1.0, 0.0, 3.0]]
    assert deficit_integral(d, a, 0.5) == pytest.approx(2.0)
    assert total_variation(np.array([[0.0, 2.0, 1.0]])) == pytest.approx(3.0)


def _fine_integral(t, x, a, m=200001):
    tt = np.linspace(t[0], t[-1], m)
    xx = np.interp(tt, t, x)
    aa = np.interp(tt, t, a)
    return float(np.trapezoid(np.maximum(xx - aa, 0.0), tt))


def test_positive_part_matches_fine_integration(rng):
    for _ in range(20):
        m = 8
        t = np.cumsum(rng.uniform(0.1, 2.0, m))
        t = t - t[0]
        x = rng.normal(0, 10, m)
        a = rng.normal(0, 10, m)
        assert positive_part_integral(t, x, a) == pytest.approx(
            _fine_integral(t, x, a), rel=1e-4, abs=1e-3
        )


def test_positive_part_special_cases():
    t = np.array([0.0, 1.0, 2.0])
    # both ends below: zero; both above: trapezoid; repeated knot = step allocation
    assert positive_part_integral(t, np.array([0.0, 0.0, 0.0]), np.array([1.0, 1.0, 1.0])) == 0.0
    assert positive_part_integral(t, np.array([3.0, 3.0, 3.0]), np.array([1.0, 1.0, 1.0])) == 4.0
    assert positive_part_integral(t, np.array([0.0, 2.0, 2.0]), np.array([0.0, 0.0, 0.0])) == 3.0
    tt = np.array([0.0, 1.0, 1.0, 2.0])
    xx = np.array([0.0, 4.0, 4.0, 4.0])
    aa = np.array([2.0, 2.0, 5.0, 5.0])  # allocation steps from 2 to 5 at t = 1
    # the allocation is above the demand after t = 1/2 on the rising part: exact 0.5
    assert positive_part_integral(tt, xx, aa) == pytest.approx(0.5, rel=1e-12)


def test_positive_part_rejects_bad_input():
    with pytest.raises(ValueError):
        positive_part_integral(np.array([0.0]), np.array([1.0]), np.array([1.0]))
    with pytest.raises(ValueError):
        positive_part_integral(np.array([1.0, 0.0]), np.array([1.0, 1.0]), np.array([1.0, 1.0]))


def test_estimate_from_samples_exact_for_linear_signal():
    dt = 0.01
    t = np.arange(0, 10.0 + dt / 2, dt)
    d = np.vstack([100.0 + 5.0 * t])
    a = np.full_like(d, 110.0)
    idx = np.append(np.arange(0, t.size, 20), t.size - 1)  # samples cover the whole span
    est = estimate_from_samples(t[idx], d[:, idx], a, dt, "linear")
    truth = deficit_integral(d, a, dt)
    assert est == pytest.approx(truth, rel=1e-9)


def test_sampling_study_rows():
    tr = Trace(0.1, np.linspace(0.0, 10.0, 101)[None, :], ["vm1"])
    rows = sampling_study(tr, np.full((1, 101), 4.0), [0.2, 1.0])
    assert [r["step_s"] for r in rows] == pytest.approx([0.2, 1.0])
    assert rows[0]["linear_rel_pct"] == pytest.approx(0.0, abs=1e-9)
    assert abs(rows[1]["hold_rel_pct"]) > 0.0


def test_hold_error_is_first_order_and_linear_second_order():
    dt = 0.001
    t = np.arange(0.0, 100.0, dt)
    d = (1000.0 + 300.0 * np.sin(2 * np.pi * t / 20.0))[None, :]
    a = np.full_like(d, 1100.0)
    truth = deficit_integral(d, a, dt)
    lin = [
        abs(estimate_from_samples(t[::k], d[:, ::k], a, dt, "linear") - truth) for k in (400, 200)
    ]
    hold = [
        abs(estimate_from_samples(t[::k], d[:, ::k], a, dt, "hold") - truth) for k in (400, 200)
    ]
    assert lin[0] / lin[1] > 3.0
    assert hold[0] / hold[1] < 2.5


def test_unknown_method_is_rejected():
    with pytest.raises(ValueError):
        estimate_from_samples(np.array([0.0]), np.zeros((1, 1)), np.zeros((1, 1)), 1.0, "cubic")
