"""Reconstruction of the demand between samples.

hold: the last sample is kept until the next one (a simple function, Halmos
section 23). This is what a controller sees between two polls.
linear: linear interpolation between neighbouring samples.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def hold(t_s: np.ndarray, x_s: np.ndarray, t_grid: np.ndarray) -> np.ndarray:
    """Value of the last sample at or before each grid time.

    Before the first sample the first value is used.

    Examples
    --------
    >>> import numpy as np
    >>> hold(np.array([0.0, 1.0]), np.array([5.0, 9.0]), np.array([0.5, 1.0, 2.0]))
    array([5., 9., 9.])
    """
    t_s, x_s = np.asarray(t_s, float), np.asarray(x_s, float)
    idx = np.searchsorted(t_s, np.asarray(t_grid, float), side="right") - 1
    return x_s[np.clip(idx, 0, x_s.size - 1)]


def linear(t_s: np.ndarray, x_s: np.ndarray, t_grid: np.ndarray) -> np.ndarray:
    """Linear interpolation; outside the samples the end values are kept.

    Examples
    --------
    >>> import numpy as np
    >>> linear(np.array([0.0, 2.0]), np.array([0.0, 4.0]), np.array([1.0]))
    array([2.])
    """
    return np.asarray(
        np.interp(np.asarray(t_grid, float), np.asarray(t_s, float), np.asarray(x_s, float)),
        dtype=float,
    )


METHODS: dict[str, Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]] = {
    "hold": hold,
    "linear": linear,
}
