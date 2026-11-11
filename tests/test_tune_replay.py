import numpy as np

from sydost_tracekit import (
    ReserveController,
    Trace,
    pareto_front,
    select,
    simulate,
    sweep,
    synthetic_trace,
)
from sydost_tracekit.replay import RunResult


def test_controller_moves_only_outside_the_deadband():
    ctl = ReserveController(s_target=10.0, deadband=5.0)
    assert ctl(np.array([100.0]), np.array([107.0])).tolist() == [107.0]  # inside deadband
    assert ctl(np.array([100.0]), np.array([80.0])).tolist() == [110.0]  # deficit: move
    assert ctl(np.array([100.0]), np.array([200.0])).tolist() == [110.0]  # far above target


def test_simulate_with_fixed_interval():
    tr = Trace(0.5, np.full((2, 40), 1000.0), ["vm1", "vm2"])
    run = simulate(tr, 2.0)
    assert isinstance(run, RunResult)
    assert run.polls == 10 and run.vm_samples == 20
    assert run.alloc.shape == (2, 40)
    assert np.all(run.alloc >= 1000.0)


def test_simulate_accepts_initial_allocation_and_custom_controller():
    tr = Trace(1.0, np.full((1, 6), 500.0), ["vm1"])
    run = simulate(tr, 3.0, controller=lambda d, a: a, a0=np.array([700.0]))
    assert run.n_red == 0 and run.balloon_volume == 0.0
    assert np.all(run.alloc == 700.0)


def test_sweep_and_select_on_synthetic_trace():
    tr = synthetic_trace("B", T=1800.0, dt=0.5, seed=3)
    rows = sweep(tr, [1.0, 4.0, 16.0], theta=64.0)
    assert len(rows) == 3
    costs = [r["cost"] for r in rows]
    assert costs[0] > costs[1] > costs[2]  # longer interval, fewer samples
    front = pareto_front(rows, ["cost", "D_GiBs"])
    assert front and all(r in rows for r in front)
    chosen = select(rows, {"P_pct": 100.0, "D_GiBs": 1e9}, "cost")
    assert chosen is not None and chosen["cost"] == min(costs)
    assert select(rows, {"D_GiBs": -1.0}, "cost") is None


def test_pareto_front_and_select_edge_cases():
    rows = [{"n": 10, "D": 5.0}, {"n": 5, "D": 9.0}, {"n": 12, "D": 6.0}, {"n": 4, "D": 20.0}]
    front = pareto_front(rows, ["n", "D"])
    assert {(r["n"], r["D"]) for r in front} == {(10, 5.0), (5, 9.0), (4, 20.0)}
    assert select(rows, {"D": 10.0}, "n") == {"n": 5, "D": 9.0}
    assert select(rows, {"D": 10.0}, "n", maximize=True) == {"n": 12, "D": 6.0}
    assert select(rows, {"D": 1.0}, "n") is None


def test_synthetic_is_reproducible_and_scenarios_differ():
    a1 = synthetic_trace("A", T=120.0, dt=0.5, seed=7)
    a2 = synthetic_trace("A", T=120.0, dt=0.5, seed=7)
    assert np.array_equal(a1.d, a2.d)
    c = synthetic_trace("C", T=120.0, dt=0.5, seed=7)
    assert c.n_vm == 4 and c.meta["scenario"] == "C"


def test_synthetic_default_and_custom_profiles():
    from sydost_tracekit import VmProfile

    tr = synthetic_trace([VmProfile(gap=20.0, active=(10.0, 30.0))], T=200.0, dt=0.5, seed=2)
    assert tr.n_vm == 1 and tr.meta["scenario"] == "custom"
    assert tr.d.min() > 0.0
