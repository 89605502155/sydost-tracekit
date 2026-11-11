"""Replay of a reserve controller on a demand trace, with fixed-interval polling.

At each poll the controller sees the demand and sets the new allocation; the
allocation is constant between polls. The balloon is instant and the host pool
is assumed sufficient. These are the assumptions for comparing monitoring
strategies on the same trace; the chosen variants are checked on a real system.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .trace import Trace

Controller = Callable[[np.ndarray, np.ndarray], np.ndarray]


class ReserveController:
    """Controller "demand plus reserve" with a dead band.

    The target of a machine is the demand plus ``s_target``. A change is applied
    if it is larger than ``deadband`` or if the machine already has a deficit.

    Examples
    --------
    >>> import numpy as np
    >>> ctl = ReserveController(s_target=10.0, deadband=5.0)
    >>> ctl(np.array([100.0, 100.0]), np.array([95.0, 200.0])).tolist()
    [110.0, 110.0]
    """

    def __init__(self, s_target: float = 256.0, deadband: float = 64.0) -> None:
        self.s_target = float(s_target)
        self.deadband = float(deadband)

    def __call__(self, d: np.ndarray, a: np.ndarray) -> np.ndarray:
        """Return the new allocation for the demand ``d`` and the current allocation ``a``."""
        target = d + self.s_target
        move = (a < d) | (np.abs(target - a) > self.deadband)
        return np.where(move, target, a)


@dataclass
class RunResult:
    """Outcome of a replay: the allocation on the trace grid and the cost of monitoring."""

    alloc: np.ndarray
    polls: int
    n_red: int
    balloon_volume: float

    @property
    def vm_samples(self) -> int:
        """Number of machine samples taken (cost of monitoring)."""
        return int(self.polls * self.alloc.shape[0])


def simulate(
    trace: Trace,
    interval_s: float,
    controller: Controller | None = None,
    a0: np.ndarray | None = None,
) -> RunResult:
    """Replay with one polling interval for all machines.

    Examples
    --------
    >>> import numpy as np
    >>> tr = Trace(0.5, np.full((1, 40), 1000.0), ["vm1"])
    >>> run = simulate(tr, 2.0)
    >>> run.polls, run.alloc.shape
    (10, (1, 40))
    """
    ctl = controller or ReserveController()
    dt, d = trace.dt, trace.d
    n = d.shape[1]
    steps = max(1, round(interval_s / dt))
    a = (
        np.array(a0, dtype=float)
        if a0 is not None
        else d[:, 0] + float(getattr(ctl, "s_target", 0.0))
    )
    alloc = np.empty_like(d)
    k = 0
    polls = n_red = 0
    volume = 0.0
    while k < n:
        a_new = np.asarray(ctl(d[:, k], a), dtype=float)
        nu = a_new - a
        changed = bool(np.any(nu != 0.0))
        volume += float(np.abs(nu).sum())
        n_red += int(changed)
        polls += 1
        alloc[:, k : k + steps] = a_new[:, None]
        a = a_new
        k += steps
    return RunResult(alloc, polls, n_red, volume)
