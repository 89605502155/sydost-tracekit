"""Shared fixtures: a reproducible generator and a fake procfs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

MEMINFO = """MemTotal:        8215296 kB
MemFree:         5000000 kB
MemAvailable:    7660288 kB
Cached:           900000 kB
SwapTotal:       1048572 kB
SwapFree:        1048572 kB
"""
PSI = """some avg10=0.00 avg60=0.00 avg300=0.00 total=1234
full avg10=0.00 avg60=0.00 avg300=0.00 total=567
"""
VMSTAT = "pgmajfault 2582\npswpin 0\npswpout 3\noom_kill 0\nnr_free_pages 10\n"


@pytest.fixture
def rng() -> np.random.Generator:
    """A reproducible random generator."""
    return np.random.default_rng(20261111)


@pytest.fixture
def fake_proc(tmp_path: Path) -> Path:
    """A procfs with meminfo, vmstat and the memory pressure file."""
    root = tmp_path / "proc"
    (root / "pressure").mkdir(parents=True)
    (root / "meminfo").write_text(MEMINFO, encoding="ascii")
    (root / "vmstat").write_text(VMSTAT, encoding="ascii")
    (root / "pressure" / "memory").write_text(PSI, encoding="ascii")
    return root
