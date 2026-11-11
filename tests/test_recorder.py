import ast
import csv
import json
from pathlib import Path

import pytest

from sydost_tracekit import recorder
from sydost_tracekit.recorder import (
    COLUMNS,
    ProcReader,
    main,
    parse_meminfo,
    parse_psi,
    parse_vmstat,
    record,
)

RECORDER = Path(recorder.__file__)


def test_parsers(fake_proc):
    text = (fake_proc / "meminfo").read_text()
    m = parse_meminfo(text + "Balloon:  524288 kB\n")
    assert m["mem_total_kib"] == 8215296 and m["balloon_kib"] == 524288
    assert parse_psi((fake_proc / "pressure" / "memory").read_text()) == {
        "psi_some_total_us": 1234,
        "psi_full_total_us": 567,
    }
    assert parse_vmstat((fake_proc / "vmstat").read_text()) == {
        "pgmajfault": 2582,
        "pswpin": 0,
        "pswpout": 3,
        "oom_kill": 0,
    }
    assert parse_psi("bogus\n") == {}


class FakeClock:
    """A clock advanced only by the fake sleep."""

    def __init__(self, sleeps=None):
        self.t = 0.0
        self.sleeps = sleeps

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += max(s, 1e-6)  # always move forward: float addition can absorb tiny sleeps


def test_recorder_schedule_is_drift_free(fake_proc, tmp_path):
    clk = FakeClock()
    out = tmp_path / "t.csv"
    summary = record(
        str(out), hz=10.0, duration=1.0, root=str(fake_proc), clock=clk, sleep=clk.sleep
    )
    assert summary["samples"] == 10  # ticks at 0, 0.1, ..., 0.9
    assert summary["late"] == 0 and summary["skipped"] == 0
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0]) == COLUMNS
    assert rows[0]["mem_total_kib"] == "8215296"
    assert rows[0]["psi_full_total_us"] == "567"


def test_late_and_skipped_ticks_are_counted(fake_proc, tmp_path):
    clk = FakeClock()
    calls = {"sleep": 0, "sample": 0}
    real_sample = ProcReader.sample

    def overshooting_sleep(s):
        calls["sleep"] += 1
        clk.t += max(s, 1e-6) + (0.07 if calls["sleep"] == 1 else 0.0)  # wakes late once

    def slow_sample(self):
        calls["sample"] += 1
        if calls["sample"] == 4:
            clk.t += 0.35  # a whole period and more: ticks are skipped
        return real_sample(self)

    ProcReader.sample = slow_sample  # type: ignore[method-assign]
    try:
        summary = record(
            str(tmp_path / "t.csv"),
            hz=10.0,
            duration=1.0,
            root=str(fake_proc),
            clock=clk,
            sleep=overshooting_sleep,
        )
    finally:
        ProcReader.sample = real_sample  # type: ignore[method-assign]
    assert summary["late"] == 1  # the tick at 0.1 started 0.07 s late
    assert summary["max_lag_s"] >= 0.07
    assert summary["skipped"] >= 2
    assert summary["samples"] < 10  # skipped ticks are not written


def test_stop_flag_ends_the_recording(fake_proc, tmp_path):
    clk = FakeClock()
    # ticks at 0.0, 0.1, 0.2 are taken before the stop time 0.25
    summary = record(
        str(tmp_path / "t.csv"),
        10.0,
        60.0,
        str(fake_proc),
        stop=lambda: clk.t >= 0.25,
        clock=clk,
        sleep=clk.sleep,
    )
    assert summary["samples"] == 3


def test_missing_sources_leave_empty_fields(tmp_path):
    root = tmp_path / "proc"
    root.mkdir()
    (root / "meminfo").write_text("MemTotal: 10 kB\nMemAvailable: 4 kB\n")
    clk = FakeClock()
    record(str(tmp_path / "t.csv"), 10.0, 0.1, str(root), clock=clk, sleep=clk.sleep)
    with (tmp_path / "t.csv").open(encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))
    assert row["psi_some_total_us"] == "" and row["pswpin"] == ""


def test_missing_meminfo_is_an_error(tmp_path):
    with pytest.raises(RuntimeError):
        ProcReader(str(tmp_path))


def test_invalid_arguments():
    with pytest.raises(ValueError):
        record("x.csv", hz=0.0, duration=1.0)


def test_main_writes_csv_and_summary(fake_proc, tmp_path, capsys):
    out = tmp_path / "m.csv"
    assert (
        main(["--hz", "20", "--duration", "0.2", "--out", str(out), "--root", str(fake_proc)]) == 0
    )
    summary = json.loads((tmp_path / "m.csv.json").read_text())
    assert summary["samples"] >= 3
    assert json.loads(capsys.readouterr().out)["hz"] == 20


def test_recorder_is_standard_library_only():
    """The guest file must import nothing outside the standard library and itself."""
    tree = ast.parse(RECORDER.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add(node.module.split(".")[0])
    import sys

    stdlib = set(sys.stdlib_module_names)
    assert names <= stdlib, names - stdlib


@pytest.mark.skipif(not Path("/proc/meminfo").exists(), reason="needs Linux procfs")
def test_real_proc_for_two_seconds_at_ten_hz(tmp_path):
    out = tmp_path / "real.csv"
    summary = record(str(out), hz=10.0, duration=1.0)
    assert summary["samples"] >= 5
    assert summary["cpu_share"] < 0.5
