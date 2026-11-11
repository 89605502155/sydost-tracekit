"""Quickstart: the accumulated deficit of a synthetic trace and its estimate from samples."""

from sydost_tracekit import deficit_integral, estimate_from_samples, simulate, synthetic_trace

tr = synthetic_trace("A", T=600.0, dt=0.1, seed=7)  # reference trace, step 0.1 s
run = simulate(tr, interval_s=4.0)  # allocation of a controller polled every 4 s
D = deficit_integral(tr.d, run.alloc, tr.dt)
est = estimate_from_samples(tr.t[::20], tr.d[:, ::20], run.alloc, tr.dt, "linear")
print(f"D = {D:.1f} MiB*s, linear estimate from 2 s samples = {est:.1f} MiB*s")
