# Bounds and theory

## The estimate from samples

Let `a` be the allocation (known exactly from the host journal), and `d` the demand.
The deficit is `f = (d − a)⁺` and `D = ∫ f dt`. Samples of `d` at step `ℓ`, held
until the next sample, define a simple function `d_ℓ`. The estimate is

    D_ℓ = ∫ (d_ℓ − a)⁺ dt.

As `ℓ → 0`, `d_ℓ → d` almost everywhere, and by the Lebesgue dominated convergence theorem
`D_ℓ → D` (the integrands are bounded by the maximum memory plus the reserve).

## Statement 4.1: hold

    |D_ℓ − D| ≤ ℓ · V(d),

where `V(d)` is the total variation of the demand. It follows from `|x⁺ − y⁺| ≤ |x − y|`.
The bound is valid and of first order in `ℓ`, but it counts variation at all times.

```python
import numpy as np
from sydost_tracekit import hold_error_bound

print(hold_error_bound(np.array([[0.0, 2.0, 1.0]]), 0.5))
```

## Refined hold bound

Let `x_k` be the held value at the fine point `k`. The error of a point is nonzero only if
the demand or the held value is above the allocation. Pointwise,

    −(d_k − max(x_k, a_k))⁺  ≤  (estimate − exact at k)  ≤  (x_k − max(d_k, a_k))⁺,

and summing over the fine grid with step `dt` gives

    −dt Σ (d_k − max(x_k, a_k))⁺  ≤  D_ℓ − D  ≤  dt Σ (x_k − max(d_k, a_k))⁺.

The lower bound counts only the rises of the demand above the allocation, the upper bound
only the falls of the held value above it. It is never looser than `ℓ·V(d)`, and it is much
tighter when the demand stays below the allocation.

```python
from sydost_tracekit import hold_error_bounds_refined, simulate, synthetic_trace

tr = synthetic_trace("A", T=600.0, dt=0.1, seed=7)
alloc = simulate(tr, interval_s=4.0).alloc
lo, hi = hold_error_bounds_refined(tr.d, alloc, tr.dt, ell=4.0)
print(f"refined: [{lo:.1f}, {hi:.1f}] MiB*s")
```

## Statement 4.2: linear interpolation

If `d` is `L`-Lipschitz with `K` kinks and `|d''| ≤ M` away from the kinks, then

    |D_lin − D| ≤ ℓ² · (T·M/12 + K·L/3).

On a smooth step the interpolation error is at most `M·u·(ℓ − u)/2` (u is the time from the
start of the step), and its integral is `M·ℓ³/12`. On a step with a kink the error is at most
`2L·u·(ℓ − u)/ℓ`, and its integral `L·ℓ²/3`. Summing over the steps gives the statement.
The standard error estimate of linear interpolation is the reference for the derivation.
The constants are estimated from a reference trace by `estimate_constants`; for a noisy trace
`M` and `K` are large and the bound is loose.

## Exact integral of the positive part

On each segment of a piecewise linear signal, `g = x − a` is linear. The integral of its
positive part follows from the crossing point with zero, so the integral of `(x − a)⁺` is
exact:

```python
import numpy as np
from sydost_tracekit import positive_part_integral

t = np.array([0.0, 1.0, 2.0])
x = np.array([0.0, 4.0, 0.0])
a = np.array([2.0, 2.0, 2.0])
print(positive_part_integral(t, x, a))
```

## What sampling rate is needed?

For an admissible absolute error `E` (MiB·s), the admissible step is the largest `ℓ` for which
the bound of the method does not exceed `E`: `ℓ = E / V` for hold, `ℓ = sqrt(E / C)` for
linear, with `C = Σ (T·M/12 + K·L/3)` over the machines. `plan_sampling` picks the method with
the larger step, that is, the lower rate.

```python
from sydost_tracekit import estimate_constants, plan_sampling, synthetic_trace

tr = synthetic_trace("B", T=600.0, dt=0.1, seed=7)
plan = plan_sampling(1e4, estimate_constants(tr.d, tr.dt))
print(plan.method, round(plan.step_s, 3), round(plan.rate_hz, 3))
```

## Scope

The bounds are for the reconstruction of the demand. They assume that the allocation is
known exactly, and that the balloon is instant. Synthetic traces are for debugging; the
conclusions of a study must rest on traces of a real system.
