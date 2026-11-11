"""Synthetic demand traces for debugging and for preliminary estimates.

The demand is a base level plus a slow drift, an Ornstein-Uhlenbeck noise and
bursts. A burst rises with finite speed, holds and falls. Scenarios A, B, C
follow the scheme of the earlier memo: A - identical machines with Poisson bursts,
B - identical machines whose bursts cluster into active periods, C - unlike
machines with mean pauses from 60 s to 3600 s.

Scenario D is held out: it is never used to choose defaults, only to validate
bounds and the sampling planner. It mixes periodic bursts with a bursty machine.

For the same seed, A, B and C reproduce the arrays of the prototype package
``kvmsim`` (same order of the random draws and the same floating-point
operations of the noise recursion). The noise recursion is a first-order
linear filter; it is written as a plain loop, so scipy is not needed.

Synthetic traces are for debugging only: conclusions of a study must rest on
traces of a real system.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .trace import Trace


@dataclass
class VmProfile:
    """Load profile of one machine.

    gap : mean pause between bursts, s (exponential).
    up, down : ranges of the rise and fall speed, MiB/s (log-uniform).
    amp : range of the amplitude, MiB. hold : range of the holding time, s.
    active : (A, Q) mean lengths of active and quiet periods, s; None means always active.
    gap_quiet : mean pause in quiet periods, s.
    base : range of the base level, MiB.
    drift_amp, drift_period : sinusoidal drift.
    noise_sd, noise_tau : standard deviation (MiB) and correlation time (s) of the noise.
    period : if given, bursts follow a schedule with this mean spacing, s, instead of
        the exponential pauses (the fields gap, active and gap_quiet are then unused).
    jitter : relative uniform jitter of the periodic spacing, in [0, 1).
    """

    gap: float = 150.0
    up: tuple[float, float] = (50.0, 400.0)
    amp: tuple[float, float] = (256.0, 2048.0)
    hold: tuple[float, float] = (5.0, 90.0)
    down: tuple[float, float] = (20.0, 200.0)
    active: tuple[float, float] | None = None
    gap_quiet: float = 1500.0
    base: tuple[float, float] = (1024.0, 2048.0)
    drift_amp: float = 200.0
    drift_period: float = 1800.0
    noise_sd: float = 20.0
    noise_tau: float = 5.0
    period: float | None = None
    jitter: float = 0.0


SCENARIOS: dict[str, list[VmProfile]] = {
    "A": [VmProfile() for _ in range(4)],
    "B": [VmProfile(gap=40.0, active=(300.0, 900.0)) for _ in range(4)],
    "C": [
        VmProfile(gap=60.0, up=(100.0, 400.0)),
        VmProfile(gap=300.0, up=(50.0, 200.0)),
        VmProfile(gap=1200.0, up=(20.0, 80.0)),
        VmProfile(gap=3600.0, up=(10.0, 50.0), amp=(128.0, 512.0)),
    ],
}

# Held out: not used for choosing any default; for validation of bounds and planner.
HELDOUT_SCENARIOS: dict[str, list[VmProfile]] = {
    "D": [
        VmProfile(period=600.0, jitter=0.1, amp=(512.0, 1024.0), up=(100.0, 300.0)),
        VmProfile(period=600.0, jitter=0.1, amp=(512.0, 1024.0), up=(100.0, 300.0)),
        VmProfile(gap=120.0, active=(600.0, 600.0), up=(50.0, 400.0)),
        VmProfile(period=1800.0, jitter=0.2, noise_sd=40.0, noise_tau=30.0),
    ],
}


def synthetic_trace(
    scenario: str | list[VmProfile] | None = None,
    T: float = 7200.0,
    dt: float = 0.1,
    seed: int = 7,
) -> Trace:
    """Synthetic trace for a scenario name (A, B, C, D) or a list of profiles.

    Examples
    --------
    >>> tr = synthetic_trace("A", T=60.0, dt=0.5, seed=1)
    >>> tr.n_vm, tr.n
    (4, 120)
    """
    if scenario is None:
        scenario = "A"
    if isinstance(scenario, str):
        label = scenario
        if scenario in SCENARIOS:
            profiles = SCENARIOS[scenario]
        elif scenario in HELDOUT_SCENARIOS:
            profiles = HELDOUT_SCENARIOS[scenario]
        else:
            raise ValueError(f"unknown scenario {scenario!r}")
    else:
        label, profiles = "custom", scenario
    rng = np.random.default_rng(seed)
    n = round(T / dt)
    t = np.arange(n) * dt
    d = np.empty((len(profiles), n))

    def loguniform(lo_hi: tuple[float, float]) -> float:
        return math.exp(rng.uniform(math.log(lo_hi[0]), math.log(lo_hi[1])))

    for i, p in enumerate(profiles):
        base = rng.uniform(*p.base)
        phase = rng.uniform(0.0, 2.0 * np.pi)
        drift = p.drift_amp * np.sin(2.0 * np.pi * t / p.drift_period + phase)
        noise = _ou_noise(rng, n, dt, p.noise_sd, p.noise_tau)
        active = _active_mask(rng, n, dt, T, p.active)
        bursts = np.zeros(n)
        t0 = 0.0
        while True:
            k0 = min(int(t0 / dt), n - 1)
            t0 += _next_gap(rng, p, bool(active[k0]))
            if t0 >= T:
                break
            amp = rng.uniform(*p.amp)
            up, down = loguniform(p.up), loguniform(p.down)
            hold = rng.uniform(*p.hold)
            t_up, t_down = amp / up, amp / down
            ka = max(int(t0 / dt), 0)
            kb = min(int((t0 + t_up + hold + t_down) / dt) + 2, n)
            seg = t[ka:kb] - t0
            shape = np.zeros(kb - ka)
            rise = (seg >= 0.0) & (seg < t_up)
            shape[rise] = up * seg[rise]
            plateau = (seg >= t_up) & (seg < t_up + hold)
            shape[plateau] = amp
            fall = (seg >= t_up + hold) & (seg < t_up + hold + t_down)
            shape[fall] = amp - down * (seg[fall] - t_up - hold)
            bursts[ka:kb] += shape
            t0 += t_up + hold + t_down
        d[i] = base + drift + noise + bursts
    names = [f"vm{i + 1}" for i in range(len(profiles))]
    return Trace(dt, d, names, {"scenario": label, "seed": seed})


def _next_gap(rng: np.random.Generator, p: VmProfile, active_now: bool) -> float:
    """Pause to the next burst, s: exponential, or periodic with a relative jitter."""
    if p.period is not None:
        if not 0.0 <= p.jitter < 1.0:
            raise ValueError("jitter must lie in [0, 1)")
        return p.period * (1.0 + p.jitter * (2.0 * rng.random() - 1.0))
    return rng.exponential(p.gap if active_now else p.gap_quiet)


def _ou_noise(rng: np.random.Generator, n: int, dt: float, sd: float, tau: float) -> np.ndarray:
    """Discrete Ornstein-Uhlenbeck process with stationary standard deviation sd.

    The recursion x[k] = phi * x[k-1] + shock[k] is the first-order filter
    lfilter([1], [1, -phi]); the operations are performed in the same order.
    """
    phi = 1.0 - dt / tau
    sigma = sd * math.sqrt(2.0 / tau)
    shocks = (rng.standard_normal(n) * sigma * math.sqrt(dt)).tolist()
    out = [0.0] * n
    x = 0.0
    for k, s in enumerate(shocks):
        x = phi * x + s
        out[k] = x
    return np.asarray(out, dtype=float)


def _active_mask(
    rng: np.random.Generator, n: int, dt: float, T: float, active: tuple[float, float] | None
) -> np.ndarray:
    """Boolean mask of the active periods; all True when no pattern is given."""
    mask = np.ones(n, dtype=bool)
    if active is None:
        return mask
    mask[:] = False
    tt = 0.0
    state = rng.random() < active[0] / sum(active)
    t = np.arange(n) * dt
    while tt < T:
        length = rng.exponential(active[0] if state else active[1])
        if state:
            mask[(t >= tt) & (t < tt + length)] = True
        tt += length
        state = not state
    return mask
