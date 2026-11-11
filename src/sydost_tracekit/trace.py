"""Memory demand traces on a uniform time grid, and their file format.

A trace holds the demand d[i, k] of virtual machine i at the moment k * dt,
in MiB; time is in seconds. The CSV file has the header ``t_s,<vm1>,<vm2>,...``
and one row per grid point. The sidecar ``<name>.json`` (optional) holds the
metadata. See docs/en/trace-format.md.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


class TraceFormatError(ValueError):
    """The file or the array does not satisfy the trace format."""


@dataclass
class Trace:
    """Demand d[i, k] of virtual machine i at time k * dt, MiB.

    Parameters
    ----------
    dt : float
        Grid step, s (positive).
    d : array_like
        Demand, shape (n_vm, n) or (n,) for one machine. Values must be finite.
    names : list of str
        One unique name per row of ``d``.
    meta : dict
        Free metadata (scenario, seed, source file).

    Examples
    --------
    >>> tr = Trace(0.5, [[1.0, 2.0, 3.0]], ["vm1"])
    >>> tr.n_vm, tr.n, tr.T
    (1, 3, 1.5)
    """

    dt: float
    d: np.ndarray
    names: list[str]
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Check the shape, the values and the names."""
        if not self.dt > 0:
            raise TraceFormatError("the grid step dt must be positive")
        self.d = np.atleast_2d(np.asarray(self.d, dtype=float))
        if self.d.ndim != 2 or self.d.shape[1] < 1:
            raise TraceFormatError("demand must have shape (n_vm, n) with n >= 1")
        if not np.all(np.isfinite(self.d)):
            raise TraceFormatError("demand contains NaN or infinite values")
        if len(self.names) != self.d.shape[0]:
            raise TraceFormatError("the number of names differs from the number of rows")
        if len(set(self.names)) != len(self.names):
            raise TraceFormatError("virtual machine names must be unique")
        if any(not name or "," in name for name in self.names):
            raise TraceFormatError("names must be non-empty and contain no commas")

    @property
    def n_vm(self) -> int:
        """Number of virtual machines."""
        return int(self.d.shape[0])

    @property
    def n(self) -> int:
        """Number of grid points."""
        return int(self.d.shape[1])

    @property
    def T(self) -> float:
        """Length of the trace, s."""
        return self.n * self.dt

    @property
    def t(self) -> np.ndarray:
        """Grid times k * dt, s."""
        return np.arange(self.n) * self.dt

    def window(self, t0: float, t1: float) -> Trace:
        """Return the part of the trace on [t0, t1)."""
        k0 = max(round(t0 / self.dt), 0)
        k1 = min(round(t1 / self.dt), self.n)
        return Trace(self.dt, self.d[:, k0:k1].copy(), list(self.names), dict(self.meta))

    def subset(self, names: list[str]) -> Trace:
        """Return the trace of the listed machines only."""
        idx = [self.names.index(x) for x in names]
        return Trace(self.dt, self.d[idx].copy(), list(names), dict(self.meta))


def save_trace(trace: Trace, path: str | Path, sidecar: bool = True) -> None:
    """Write the trace as CSV, and the metadata as ``<path>.json`` when asked.

    Examples
    --------
    >>> import tempfile, os
    >>> p = os.path.join(tempfile.mkdtemp(), "t.csv")
    >>> save_trace(Trace(1.0, [[1.0, 2.0]], ["vm1"]), p, sidecar=False)
    >>> with open(p) as fh:
    ...     print(fh.readline().strip())
    t_s,vm1
    """
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["t_s", *trace.names])
        for k in range(trace.n):
            writer.writerow([f"{k * trace.dt:.6f}", *(f"{x:.3f}" for x in trace.d[:, k])])
    if sidecar:
        meta = {"dt": trace.dt, "names": trace.names, **trace.meta}
        Path(str(path) + ".json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
        )


def load_trace(path: str | Path) -> Trace:
    """Read a trace CSV and check the format (see :class:`TraceFormatError`).

    The grid must be uniform up to rounding of the time column: the tolerance is
    the larger of 1e-6 s and 1e-3 dt.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as fh:
        rows = [row for row in csv.reader(fh) if row]
    if len(rows) < 2:
        raise TraceFormatError(f"{path}: no data rows")
    header, body = rows[0], rows[1:]
    if header[0] != "t_s" or len(header) < 2:
        raise TraceFormatError(f"{path}: the first column must be t_s, followed by VM columns")
    if any(len(row) != len(header) for row in body):
        raise TraceFormatError(f"{path}: a row has a different number of fields")
    try:
        data = np.array(body, dtype=float)
    except ValueError as err:
        raise TraceFormatError(f"{path}: non-numeric value ({err})") from err
    if not np.all(np.isfinite(data)):
        raise TraceFormatError(f"{path}: empty or non-finite values")
    steps = np.diff(data[:, 0])
    dt = float(np.median(steps))
    if dt <= 0 or np.max(np.abs(steps - dt)) > max(1e-6, 1e-3 * dt):
        raise TraceFormatError(f"{path}: the time grid is not uniform")
    meta: dict[str, Any] = {"source": str(path)}
    sidecar = Path(str(path) + ".json")
    if sidecar.exists():
        meta.update(json.loads(sidecar.read_text(encoding="utf-8")))
    return Trace(dt, data[:, 1:].T.copy(), header[1:], meta)
