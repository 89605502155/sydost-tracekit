#!/usr/bin/env python3
"""Guest memory recorder: Python standard library only, one file.

The file is copied into a guest virtual machine as it is and run with
Python 3.11 to 3.14, the versions on which the library tests run (older ones are not tested)::

    python3 recorder.py --hz 10 --duration 7200 --out trace_vm1.csv

It must not import anything from this package, so that it stays a single file
(see docs/en/recorder-deployment.md). Every ``hz`` seconds it writes one CSV row
with the fields of /proc/meminfo, /proc/vmstat and the memory pressure file
(PSI). An empty value means that the source is not available. The file
``<out>.json`` next to the CSV holds the summary: the number of samples, late
and skipped ticks, and the CPU share of the recorder itself.

The schedule is drift-free: tick ``k`` is due at ``start + k / hz``, so the
rate does not decay when a sample is slow. When the recorder wakes up after
the due time by more than half a period, the tick counts as late. When it is
behind by a whole period or more, the missed ticks are skipped and counted.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import signal
import socket
import time
from collections.abc import Callable
from typing import Any

MEMINFO = {
    "MemTotal": "mem_total_kib",
    "MemFree": "mem_free_kib",
    "MemAvailable": "mem_available_kib",
    "Cached": "cached_kib",
    "SwapTotal": "swap_total_kib",
    "SwapFree": "swap_free_kib",
    "Balloon": "balloon_kib",
}
VMSTAT = ("pgmajfault", "pswpin", "pswpout", "oom_kill")
COLUMNS = [
    "t_mono_s",
    "t_real_s",
    *MEMINFO.values(),
    "psi_some_total_us",
    "psi_full_total_us",
    *VMSTAT,
]


def parse_meminfo(text: str) -> dict[str, int]:
    r"""Return the known /proc/meminfo fields in KiB, keyed by column name.

    >>> parse_meminfo("MemTotal:  100 kB\nMemAvailable: 40 kB\n")
    {'mem_total_kib': 100, 'mem_available_kib': 40}
    """
    out: dict[str, int] = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        if key in MEMINFO and rest.split():
            out[MEMINFO[key]] = int(rest.split()[0])
    return out


def parse_psi(text: str) -> dict[str, int]:
    r"""Return the cumulative stall times (microseconds) of a PSI file.

    >>> parse_psi("some avg10=0.0 total=12\nfull avg10=0.0 total=3\n")
    {'psi_some_total_us': 12, 'psi_full_total_us': 3}
    """
    out: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] in ("some", "full"):
            for part in parts[1:]:
                if part.startswith("total="):
                    out[f"psi_{parts[0]}_total_us"] = int(part[6:])
    return out


def parse_vmstat(text: str) -> dict[str, int]:
    r"""Return the selected counters of /proc/vmstat.

    >>> parse_vmstat("pgmajfault 7\npswpin 0\nnr_free_pages 9\n")
    {'pgmajfault': 7, 'pswpin': 0}
    """
    out: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in VMSTAT:
            out[parts[0]] = int(parts[1])
    return out


class ProcReader:
    """Keep the /proc files open and read them from the start on each sample."""

    def __init__(self, root: str = "/proc") -> None:
        self.files: dict[str, Any] = {}
        for name, rel in [("meminfo", "meminfo"), ("vmstat", "vmstat"), ("psi", "pressure/memory")]:
            try:
                self.files[name] = open(os.path.join(root, rel), "rb")  # noqa: SIM115
            except OSError:
                self.files[name] = None
        if self.files["meminfo"] is None:
            raise RuntimeError(f"no {os.path.join(root, 'meminfo')}")

    def _read(self, name: str) -> str:
        fh = self.files[name]
        if fh is None:
            return ""
        fh.seek(0)
        return str(fh.read().decode("ascii", "replace"))

    def sample(self) -> dict[str, float | int]:
        """Return one row of the trace as a dict of column name to value."""
        row: dict[str, float | int] = {"t_mono_s": time.monotonic(), "t_real_s": time.time()}
        row.update(parse_meminfo(self._read("meminfo")))
        row.update(parse_psi(self._read("psi")))
        row.update(parse_vmstat(self._read("vmstat")))
        return row

    def close(self) -> None:
        """Close all open /proc files."""
        for fh in self.files.values():
            if fh is not None:
                fh.close()


def record(
    out_path: str,
    hz: float,
    duration: float,
    root: str = "/proc",
    stop: Callable[[], bool] = lambda: False,
    flush_every: int = 50,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    r"""Write a trace of memory counters and return the summary.

    Parameters
    ----------
    out_path : str
        CSV file to write (overwritten).
    hz : float
        Sampling frequency, Hz.
    duration : float
        Length of the recording, s.
    root : str
        Root of the procfs (a fake root is used in the tests).
    stop : callable
        Returns True to stop early (signal handler).
    flush_every : int
        Flush the file after this many rows.
    clock, sleep : callable
        Injected for deterministic tests.

    Returns
    -------
    dict
        Samples, late and skipped ticks, the largest lag, wall time, CPU time and
        CPU share of the recorder, frequency, host and kernel.

    Examples
    --------
    >>> import tempfile, os
    >>> root = tempfile.mkdtemp()
    >>> os.mkdir(os.path.join(root, "pressure"))
    >>> with open(os.path.join(root, "meminfo"), "w") as fh:
    ...     _ = fh.write("MemTotal: 10 kB\nMemAvailable: 4 kB\n")
    >>> summary = record(os.path.join(root, "t.csv"), hz=50, duration=0.05, root=root)
    >>> summary["samples"] >= 1
    True
    """
    if hz <= 0 or duration <= 0:
        raise ValueError("hz and duration must be positive")
    period = 1.0 / hz
    reader = ProcReader(root)
    start = clock()
    cpu0 = time.process_time()
    k = 0
    n = late = skipped = 0
    max_lag = 0.0
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, restval="")
        writer.writeheader()
        try:
            while not stop():
                now = clock() - start
                if now >= duration:
                    break
                due = k * period
                if now < due:
                    sleep(due - now)
                    continue
                lag = now - due
                writer.writerow(reader.sample())
                n += 1
                max_lag = max(max_lag, lag)
                if lag > period / 2:
                    late += 1
                if n % flush_every == 0:
                    fh.flush()
                # The next tick is the first one not yet behind by a whole period: a tick that
                # is overdue by less than a period is run at once (not skipped), a tick of the
                # current period is never sampled twice (next_k > k). The epsilon guards rounding.
                done = clock() - start
                next_k = max(k + 1, math.floor(done / period + 1e-9))
                skipped += next_k - (k + 1)
                k = next_k
        finally:
            reader.close()
    wall = clock() - start
    cpu = time.process_time() - cpu0
    return {
        "samples": n,
        "late": late,
        "skipped": skipped,
        "max_lag_s": max_lag,
        "hz": hz,
        "duration_s": duration,
        "wall_s": wall,
        "cpu_s": cpu,
        "cpu_share": cpu / wall if wall > 0 else 0.0,
        "host": socket.gethostname(),
        "kernel": platform.release(),
    }


def main(argv: list[str] | None = None) -> int:
    """Command line entry point of the guest recorder."""
    ap = argparse.ArgumentParser(description="Guest memory recorder (stdlib only)")
    ap.add_argument("--hz", type=float, default=10.0, help="sampling frequency, Hz")
    ap.add_argument("--duration", type=float, default=600.0, help="length, s")
    ap.add_argument("--out", default="trace.csv")
    ap.add_argument("--root", default="/proc", help="procfs root (for tests)")
    args = ap.parse_args(argv)
    flag = {"stop": False}

    def on_signal(_sig: int, _frame: object) -> None:
        flag["stop"] = True

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    summary = record(args.out, args.hz, args.duration, args.root, lambda: flag["stop"])
    with open(args.out + ".json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
