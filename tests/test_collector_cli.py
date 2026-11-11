import builtins
import csv
import sys
from pathlib import Path

import numpy as np
import pytest

from sydost_tracekit import Trace, save_trace, synthetic_trace
from sydost_tracekit.cli import build_parser, main
from sydost_tracekit.collector import KEYS, collect, connect


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class FakeDom:
    def __init__(self, last_update=0):
        self.period = None
        self.last_update = last_update

    def setMemoryStatsPeriod(self, period, flags):
        self.period = period

    def memoryStats(self):
        return {"actual": 2097152, "available": 8388608, "last_update": self.last_update}


def _clock():
    state = {"t": 0.0}

    def clock():
        return state["t"]

    def sleep(s):
        state["t"] += max(s, 1e-6)

    return clock, sleep


def test_collector_with_fake_domains(tmp_path):
    clock, sleep = _clock()
    doms = {"vm1": FakeDom(), "vm2": FakeDom()}
    n = collect(doms, hz=2.0, duration=5.0, out=str(tmp_path / "h.csv"), clock=clock, sleep=sleep)
    assert n == 20 and doms["vm1"].period == 1
    rows = _read_rows(tmp_path / "h.csv")
    assert rows[0]["vm"] == "vm1" and rows[0]["actual"] == "2097152"
    assert rows[0]["usable"] == ""  # key absent in the fake snapshot
    assert set(KEYS) <= set(rows[0])


def test_collector_age_of_snapshot_and_no_period(tmp_path):
    clock, sleep = _clock()
    dom = FakeDom(last_update=0)  # snapshot taken at the epoch: very old
    collect(
        {"vm1": dom},
        hz=1.0,
        duration=1.0,
        out=str(tmp_path / "h.csv"),
        set_period=False,
        clock=clock,
        sleep=sleep,
    )
    assert dom.period is None
    row = _read_rows(tmp_path / "h.csv")[0]
    assert float(row["age_s"]) > 1e6
    assert row["usable"] == ""


def test_collector_empty_last_update_gives_empty_age(tmp_path):
    clock, sleep = _clock()

    class NoStamp(FakeDom):
        def memoryStats(self):
            return {"actual": 1}

    collect(
        {"vm1": NoStamp()},
        hz=1.0,
        duration=1.0,
        out=str(tmp_path / "h.csv"),
        clock=clock,
        sleep=sleep,
    )
    row = _read_rows(tmp_path / "h.csv")[0]
    assert row["age_s"] == ""


def test_collector_rejects_bad_rates(tmp_path):
    with pytest.raises(ValueError):
        collect({}, hz=0.0, duration=1.0, out=str(tmp_path / "x.csv"))


def test_connect_without_libvirt_explains_the_extra(monkeypatch):
    real_import = builtins.__import__

    def no_libvirt(name, *args, **kwargs):
        if name == "libvirt":
            raise ImportError("no libvirt")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_libvirt)
    monkeypatch.delitem(sys.modules, "libvirt", raising=False)
    with pytest.raises(ImportError, match="sydost-tracekit\\[kvm\\]"):
        connect("qemu:///system", ["vm1"])


def test_cli_record(fake_proc, tmp_path, capsys):
    out = tmp_path / "r.csv"
    assert (
        main(
            [
                "record",
                "--hz",
                "20",
                "--duration",
                "0.2",
                "--out",
                str(out),
                "--root",
                str(fake_proc),
            ]
        )
        == 0
    )
    assert out.exists() and (tmp_path / "r.csv.json").exists()
    assert "samples" in capsys.readouterr().out


def test_cli_integrate_bound_tune(tmp_path, capsys):
    tr = synthetic_trace("A", T=200.0, dt=0.1, seed=5)
    ref = tmp_path / "ref.csv"
    save_trace(tr, ref, sidecar=False)
    alloc = Trace(tr.dt, np.full_like(tr.d, np.percentile(tr.d, 95)), tr.names)
    alloc_path = tmp_path / "alloc.csv"
    save_trace(alloc, alloc_path, sidecar=False)

    assert main(["integrate", str(ref), "--alloc", str(alloc_path), "--steps", "0.5,2"]) == 0
    out = capsys.readouterr().out
    assert "D_true" in out and "hold_rel_pct" in out and "linear_rel_pct" in out

    assert main(["bound", str(ref), "--steps", "1,2", "--target", "1000"]) == 0
    out = capsys.readouterr().out
    assert "hold bound" in out and "rate" in out

    assert main(["tune", str(ref), "--intervals", "1,4", "--alpha", "100", "--dmax", "1e9"]) == 0
    out = capsys.readouterr().out
    assert "selected" in out


def test_cli_integrate_rejects_mismatched_allocation(tmp_path, capsys):
    ref = tmp_path / "ref.csv"
    save_trace(Trace(0.1, [[1.0, 2.0, 3.0]], ["vm1"]), ref, sidecar=False)
    bad = tmp_path / "bad.csv"
    save_trace(Trace(0.2, [[1.0, 2.0, 3.0]], ["vm1"]), bad, sidecar=False)
    assert main(["integrate", str(ref), "--alloc", str(bad)]) == 2
    assert "must have the grid" in capsys.readouterr().err


def test_cli_bound_without_target_and_tune_without_selection(tmp_path, capsys):
    ref = tmp_path / "ref.csv"
    save_trace(synthetic_trace("A", T=60.0, dt=0.5, seed=1), ref, sidecar=False)
    assert main(["bound", str(ref)]) == 0
    assert "target" not in capsys.readouterr().out
    assert main(["tune", str(ref), "--intervals", "2", "--alpha", "-1"]) == 0
    assert "no configuration" in capsys.readouterr().out


def test_cli_parser_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
    with pytest.raises(SystemExit):
        main(["--version"])
