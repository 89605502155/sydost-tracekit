"""A-priori bounds: which sampling rate gives the target error of D?"""

from sydost_tracekit import estimate_constants, plan_sampling, synthetic_trace

tr = synthetic_trace("B", T=600.0, dt=0.1, seed=7)
c = estimate_constants(tr.d, tr.dt)  # V, L, M, K from the reference trace
for target in (1e5, 1e4):
    plan = plan_sampling(target, c)
    print(
        f"target {target:g} MiB*s: {plan.method}, step {plan.step_s:.3g} s, "
        f"rate {plan.rate_hz:.3g} Hz per machine"
    )
