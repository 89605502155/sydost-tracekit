import csv

import numpy as np
import pytest

from sydost_tracekit import (
    ClockSample,
    demand,
    estimate_offset,
    fit_drift,
    guest_to_host,
    read_recorder_csv,
    recordings_to_trace,
)


def _write_recording(path, used_mib, n=50, dt=0.1, t0=100.0, balloon_kib=None):
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        cols = ["t_mono_s", "t_real_s", "mem_total_kib", "mem_available_kib"]
        if balloon_kib is not None:
            cols.append("balloon_kib")
        w.writerow(cols)
        for k in range(n):
            row = [k * dt, t0 + k * dt, 8192 * 1024, (8192 - used_mib - k) * 1024]
            if balloon_kib is not None:
                row.append(balloon_kib)
            w.writerow(row)


def test_read_and_demand(tmp_path):
    p = tmp_path / "vm1.csv"
    _write_recording(p, 1000)
    rec = read_recorder_csv(p)
    d = demand(rec, reserve_mib=256.0)
    assert d[0] == pytest.approx(1000 + 256.0)


def test_autodeflate_subtracts_balloon(tmp_path):
    p = tmp_path / "vm1.csv"
    _write_recording(p, 1000, balloon_kib=512 * 1024)
    rec = read_recorder_csv(p)
    assert demand(rec, autodeflate=True)[0] == pytest.approx(1000 - 512)
    assert demand(rec, autodeflate=True, balloon_mib=np.full(50, 100.0))[0] == pytest.approx(900)
    no_col = {k: v for k, v in rec.items() if k != "balloon_kib"}
    with pytest.raises(ValueError):
        demand(no_col, autodeflate=True)
    rec["balloon_kib"][3] = np.nan
    with pytest.raises(ValueError):
        demand(rec, autodeflate=True)


def test_read_rejects_empty_file(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("t_real_s,mem_total_kib,mem_available_kib\n")
    with pytest.raises(ValueError):
        read_recorder_csv(p)


def test_recordings_to_trace_on_common_span(tmp_path):
    a = tmp_path / "vm1.csv"
    b = tmp_path / "vm2.csv"
    _write_recording(a, 1000, n=50, t0=100.0)
    _write_recording(b, 2000, n=40, t0=101.0)  # starts later, ends earlier
    recs = {"vm1": read_recorder_csv(a), "vm2": read_recorder_csv(b)}
    tr = recordings_to_trace(recs, reserve_mib=0.0, dt=0.1)
    assert tr.names == ["vm1", "vm2"]
    assert tr.meta["t0_real_s"] == pytest.approx(101.0)
    assert tr.d[1, 0] == pytest.approx(2000.0)
    assert tr.d[0, 0] == pytest.approx(1010.0)  # vm1 at t = 101.0 s: 1000 + 10 steps
    assert 39 <= tr.d.shape[1] <= 40  # 101.0 s to 104.9 s on the 0.1 s grid


def test_recordings_to_trace_hold_and_errors(tmp_path):
    a = tmp_path / "vm1.csv"
    _write_recording(a, 1000)
    recs = {"vm1": read_recorder_csv(a)}
    tr = recordings_to_trace(recs, dt=0.1, method="hold")
    assert tr.meta["method"] == "hold"
    with pytest.raises(ValueError):
        recordings_to_trace(recs, method="cubic")
    late = {
        "vm1": {
            "t_real_s": np.array([0.0, 1.0]),
            "mem_total_kib": np.ones(2),
            "mem_available_kib": np.ones(2),
        }
    }
    no_overlap = {
        "x": {
            "t_real_s": np.array([5.0, 6.0]),
            "mem_total_kib": np.ones(2),
            "mem_available_kib": np.ones(2),
        },
        **late,
    }
    with pytest.raises(ValueError):
        recordings_to_trace(no_overlap, dt=0.1)


def test_clock_offset_uses_the_shortest_round_trip():
    samples = [ClockSample(10.0, 15.6, 10.8), ClockSample(20.0, 25.2, 20.2)]
    est = estimate_offset(samples)  # the exchange with rtt 0.2 s: midpoint 20.1
    assert est.offset_s == pytest.approx(5.1)
    assert est.uncertainty_s == pytest.approx(0.1)
    assert est.n_samples == 2
    assert guest_to_host(np.array([105.1]), est.offset_s)[0] == pytest.approx(100.0)


def test_clock_offset_rejects_bad_input():
    with pytest.raises(ValueError):
        estimate_offset([])
    with pytest.raises(ValueError):
        estimate_offset([ClockSample(2.0, 1.0, 1.0)])


def test_fit_drift_in_ppm():
    host = np.array([0.0, 1000.0, 2000.0])
    offsets = 5.0 + 2e-6 * host
    slope, intercept = fit_drift(host, offsets)
    assert slope == pytest.approx(2.0, rel=1e-6)
    assert intercept == pytest.approx(5.0, abs=1e-6)
