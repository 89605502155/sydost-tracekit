"""Refined hold bound: only the variation above the allocation matters."""

from sydost_tracekit import hold_error_bound, hold_error_bounds_refined, simulate, synthetic_trace

tr = synthetic_trace("A", T=600.0, dt=0.1, seed=7)
alloc = simulate(tr, interval_s=4.0).alloc
lo, hi = hold_error_bounds_refined(tr.d, alloc, tr.dt, ell=4.0)
plain = hold_error_bound(tr.d, 4.0)
print(f"refined: [{lo:.1f}, {hi:.1f}] MiB*s, plain l*V: {plain:.1f} MiB*s")
