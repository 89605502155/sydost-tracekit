"""Turning guest recordings into traces.

Demand: d = (MemTotal - MemAvailable) / 1024 + reserve, MiB. With
autodeflate='on' of the balloon the guest kernel already lowers MemTotal by the
balloon size, so the balloon has to be subtracted once more (see
docs/en/trace-format.md). The balloon size comes from the recorder column
balloon_kib or from a host series balloon_mib.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

import numpy as np

from .reconstruct import METHODS
from .trace import Trace


def read_recorder_csv(path: str | Path) -> dict[str, np.ndarray]:
    r"""Read a recorder CSV into arrays per column; empty values become NaN.

    Examples
    --------
    >>> import tempfile, os
    >>> p = os.path.join(tempfile.mkdtemp(), "r.csv")
    >>> with open(p, "w") as fh:
    ...     _ = fh.write("t_real_s,mem_total_kib\n1.0,100\n1.5,\n")
    >>> read_recorder_csv(p)["mem_total_kib"].tolist()
    [100.0, nan]
    """
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"empty recording {path}")
    return {
        key: np.array([float(r[key]) if r[key] != "" else np.nan for r in rows]) for key in rows[0]
    }


def demand(
    rec: Mapping[str, np.ndarray],
    reserve_mib: float = 0.0,
    autodeflate: bool = False,
    balloon_mib: np.ndarray | None = None,
) -> np.ndarray:
    """Demand of one machine from a recording, MiB.

    Examples
    --------
    >>> import numpy as np
    >>> rec = {"mem_total_kib": np.array([2048.0]), "mem_available_kib": np.array([1024.0])}
    >>> demand(rec, reserve_mib=10.0)
    array([11.])
    """
    used = (np.asarray(rec["mem_total_kib"]) - np.asarray(rec["mem_available_kib"])) / 1024.0
    if not autodeflate:
        return np.asarray(used + reserve_mib, dtype=float)
    if balloon_mib is None:
        col = rec.get("balloon_kib")
        if col is None or np.isnan(col).any():
            raise ValueError("balloon size needed: column balloon_kib or balloon_mib")
        balloon_mib = col / 1024.0
    return np.asarray(used - np.asarray(balloon_mib, float) + reserve_mib, dtype=float)


def recordings_to_trace(
    recs: Mapping[str, Mapping[str, np.ndarray]],
    reserve_mib: float = 0.0,
    dt: float = 0.1,
    method: str = "linear",
    clock: str = "t_real_s",
    autodeflate: bool = False,
) -> Trace:
    """Put the recordings of several machines on one grid over their common span.

    Parameters
    ----------
    recs : mapping
        Name of the machine to its recording (as from :func:`read_recorder_csv`).
    reserve_mib : float
        Reserve added to the demand.
    dt : float
        Grid step, s.
    method : str
        ``"linear"`` or ``"hold"`` reconstruction between the recorded rows.
    clock : str
        Time column. ``t_real_s`` is comparable across machines once the clocks
        are aligned (see :mod:`sydost_tracekit.clock`); ``t_mono_s`` only inside
        one machine.
    autodeflate : bool
        Subtract the balloon size (see :func:`demand`).
    """
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}")
    t0 = max(float(r[clock][0]) for r in recs.values())
    t1 = min(float(r[clock][-1]) for r in recs.values())
    if t1 <= t0:
        raise ValueError("the recordings do not overlap in time")
    grid = np.arange(t0, t1, dt)
    rows = [
        METHODS[method](r[clock], demand(r, reserve_mib, autodeflate), grid) for r in recs.values()
    ]
    return Trace(dt, np.vstack(rows), list(recs), {"t0_real_s": t0, "method": method})
