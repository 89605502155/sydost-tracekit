import numpy as np
import pytest

from sydost_tracekit import Trace, TraceFormatError, load_trace, save_trace


def test_trace_properties_and_views():
    tr = Trace(0.5, np.arange(12.0).reshape(2, 6), ["a", "b"], {"seed": 1})
    assert tr.n_vm == 2 and tr.n == 6 and tr.T == 3.0
    assert np.allclose(tr.t, np.arange(6) * 0.5)
    w = tr.window(1.0, 2.0)
    assert w.n == 2 and w.d[0, 0] == 2.0
    s = tr.subset(["b"])
    assert s.names == ["b"] and s.d[0, 0] == 6.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dt": 0.0, "d": [[1.0]], "names": ["a"]},
        {"dt": 1.0, "d": [[np.nan]], "names": ["a"]},
        {"dt": 1.0, "d": [[1.0]], "names": ["a", "b"]},
        {"dt": 1.0, "d": [[1.0], [2.0]], "names": ["a", "a"]},
        {"dt": 1.0, "d": [[1.0]], "names": ["a,b"]},
        {"dt": 1.0, "d": np.zeros((1, 0)), "names": ["a"]},
    ],
)
def test_trace_validation(kwargs):
    with pytest.raises(TraceFormatError):
        Trace(**kwargs)


def test_round_trip_csv_with_sidecar(tmp_path):
    tr = Trace(0.25, [[1.0, 2.5, 3.0], [0.0, 0.0, 9.0]], ["vm1", "vm2"], {"scenario": "A"})
    p = tmp_path / "t.csv"
    save_trace(tr, p)
    back = load_trace(p)
    assert back.names == ["vm1", "vm2"] and back.dt == pytest.approx(0.25)
    assert np.allclose(back.d, tr.d)
    assert back.meta["scenario"] == "A" and back.meta["dt"] == 0.25


def test_save_without_sidecar(tmp_path):
    p = tmp_path / "t.csv"
    save_trace(Trace(1.0, [[1.0, 2.0]], ["vm1"]), p, sidecar=False)
    assert not (tmp_path / "t.csv.json").exists()
    assert load_trace(p).meta["source"] == str(p)


@pytest.mark.parametrize(
    "text",
    [
        "x,vm1\n0,1\n1,2\n",  # wrong first column
        "t_s\n0\n1\n",  # no VM columns
        "t_s,vm1\n0\n",  # one data row
        "t_s,vm1\n0,1,2\n1,2\n",  # ragged rows
        "t_s,vm1\n0,abc\n1,2\n",  # not a number
        "t_s,vm1\n0,\n1,2\n",  # empty value
        "t_s,vm1\n0,1\n1,2\n3,3\n",  # non-uniform grid
    ],
)
def test_load_rejects_bad_files(tmp_path, text):
    p = tmp_path / "bad.csv"
    p.write_text(text)
    with pytest.raises(TraceFormatError):
        load_trace(p)


def test_load_tolerates_rounding_of_time(tmp_path):
    p = tmp_path / "ok.csv"
    p.write_text("t_s,vm1\n0.000000,1.0\n0.100001,2.0\n0.200000,3.0\n")
    assert load_trace(p).dt == pytest.approx(0.1, abs=1e-5)
