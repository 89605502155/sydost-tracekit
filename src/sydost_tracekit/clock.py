"""Alignment of the host and guest clocks.

The guest recorder writes wall-clock time t_real_s of the guest. The host
collector writes its own t_real_s. To compare them, the offset between the two
clocks is estimated from request-response exchanges (Cristian's algorithm): the
host notes the time before and after asking the guest for its clock.

The error of the estimate is at most half of the round trip of the exchange
used. The helper keeps the exchange with the smallest round trip.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClockSample:
    """One exchange: host time before the request, guest time, host time after."""

    t_send_host: float
    t_guest: float
    t_recv_host: float


@dataclass(frozen=True)
class ClockOffset:
    """Estimated offset guest minus host, with its bound on the error, s."""

    offset_s: float
    uncertainty_s: float
    n_samples: int


def estimate_offset(samples: Sequence[ClockSample]) -> ClockOffset:
    """Offset guest - host from the exchange with the smallest round trip.

    Examples
    --------
    >>> s = [ClockSample(100.0, 105.2, 100.4), ClockSample(200.0, 205.0, 200.2)]
    >>> est = estimate_offset(s)
    >>> round(est.offset_s, 3), round(est.uncertainty_s, 3)
    (5.0, 0.1)
    """
    if not samples:
        raise ValueError("at least one exchange is needed")
    best = min(samples, key=lambda s: s.t_recv_host - s.t_send_host)
    rtt = best.t_recv_host - best.t_send_host
    if rtt < 0:
        raise ValueError("the host received the answer before sending the request")
    midpoint = (best.t_send_host + best.t_recv_host) / 2.0
    return ClockOffset(best.t_guest - midpoint, rtt / 2.0, len(samples))


def guest_to_host(t_guest: np.ndarray, offset_s: float) -> np.ndarray:
    """Convert guest wall-clock times to host time."""
    return np.asarray(t_guest, float) - offset_s


def fit_drift(host_t: np.ndarray, offsets: np.ndarray) -> tuple[float, float]:
    """Linear fit offset = intercept + slope * host_time; slope in ppm.

    Examples
    --------
    >>> import numpy as np
    >>> slope, intercept = fit_drift(np.array([0.0, 100.0]), np.array([1.0, 1.0001]))
    >>> round(slope, 3)
    1.0
    """
    slope, intercept = np.polyfit(np.asarray(host_t, float), np.asarray(offsets, float), 1)
    return float(slope) * 1e6, float(intercept)
