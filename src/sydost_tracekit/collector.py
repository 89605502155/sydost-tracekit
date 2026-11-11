"""Host collector: memory statistics of libvirt domains at a fixed frequency.

The host path is slower than the guest recorder: QEMU asks the guest for its
statistics once per period (whole seconds, at least 1 s), and memoryStats()
returns the last snapshot (SPEC section 6.5). The collector writes the snapshot
age ``age_s = t_real_s - last_update`` so that stale snapshots are visible.

libvirt is optional and imported lazily: install with ``pip install
sydost-tracekit[kvm]``. The tests use fake domains and need no libvirt.

Example on the host::

    from sydost_tracekit.collector import connect, collect

    doms = connect("qemu:///system", ["vm1", "vm2"])
    collect(doms, hz=1, duration=600, out="host_stats.csv")
"""

from __future__ import annotations

import csv
import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol

KEYS = [
    "actual",
    "available",
    "usable",
    "unused",
    "disk_caches",
    "last_update",
    "rss",
    "swap_in",
    "swap_out",
    "major_fault",
    "minor_fault",
]
VIR_DOMAIN_AFFECT_LIVE = 1  # libvirt-domain.h: 1 << 0


class Domain(Protocol):
    """The part of the libvirt domain interface that the collector uses."""

    def setMemoryStatsPeriod(self, period: int, flags: int) -> Any:  # noqa: N802
        """Set the statistics period, s."""
        ...

    def memoryStats(self) -> Mapping[str, int]:  # noqa: N802
        """Return the last memory statistics snapshot (KiB)."""
        ...


def connect(uri: str, names: list[str]) -> dict[str, Any]:
    """Open a libvirt connection and look up the named domains.

    Raises
    ------
    ImportError
        If libvirt-python is not installed.
    """
    try:
        import libvirt
    except ImportError as err:  # pragma: no cover - needs libvirt on the host
        raise ImportError("install the extra: pip install sydost-tracekit[kvm]") from err
    conn = libvirt.open(uri)  # pragma: no cover - needs libvirt on the host
    return {n: conn.lookupByName(n) for n in names}  # pragma: no cover


def collect(
    domains: Mapping[str, Domain],
    hz: float,
    duration: float,
    out: str,
    stats_period: int = 1,
    set_period: bool = True,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Poll memoryStats() of all domains at frequency hz; return the number of rows.

    Examples
    --------
    >>> class Fake:
    ...     def setMemoryStatsPeriod(self, period, flags):
    ...         pass
    ...
    ...     def memoryStats(self):
    ...         return {"actual": 1024, "last_update": 0}
    >>> import tempfile, os
    >>> p = os.path.join(tempfile.mkdtemp(), "h.csv")
    >>> collect({"vm1": Fake()}, hz=2.0, duration=1.0, out=p, set_period=False)
    2
    """
    if hz <= 0 or duration <= 0:
        raise ValueError("hz and duration must be positive")
    if set_period:
        for dom in domains.values():
            dom.setMemoryStatsPeriod(int(stats_period), VIR_DOMAIN_AFFECT_LIVE)
    period = 1.0 / hz
    start = clock()
    n = 0
    k = 0
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["t_mono_s", "t_real_s", "vm", *KEYS, "age_s"])
        while True:
            now = clock() - start
            if now >= duration:
                break
            due = k * period
            if now < due:
                sleep(due - now)
                continue
            for name, dom in domains.items():
                st = dom.memoryStats()
                real = time.time()
                last = st.get("last_update", "")
                age = real - float(last) if last != "" else ""
                writer.writerow(
                    [
                        f"{clock():.6f}",
                        f"{real:.6f}",
                        name,
                        *(st.get(key, "") for key in KEYS),
                        f"{age:.3f}" if age != "" else "",
                    ]
                )
                n += 1
            k += 1
    return n
