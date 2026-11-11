"""Tuning: the cheapest polling interval with P(theta) <= alpha and D <= D_max."""

from sydost_tracekit import pareto_front, select, sweep, synthetic_trace

tr = synthetic_trace("C", T=600.0, dt=0.1, seed=7)
rows = sweep(tr, [1.0, 2.0, 4.0, 8.0, 16.0], theta=64.0)
front = pareto_front(rows, ["cost", "D_GiBs"])
best = select(rows, {"P_pct": 50.0, "D_GiBs": 1e9}, "cost")
print(f"Pareto points: {len(front)}")
print(f"selected interval: {best['interval_s'] if best else 'none'} s")
