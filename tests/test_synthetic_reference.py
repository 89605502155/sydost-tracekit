"""The synthetic scenarios A, B, C reproduce the prototype arrays (stored reference).

The reference file tests/data/synthetic_ref.npz was generated once from the prototype
package kvmsim (T = 120 s, dt = 0.1 s, seeds 7 and 1). The test does not import the prototype.
Achieved agreement at generation: bit-identical (max abs and rel difference 0).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from sydost_tracekit import synthetic_trace

REF = Path(__file__).parent / "data" / "synthetic_ref.npz"


def test_scenarios_match_prototype_reference():
    ref = np.load(REF)
    worst_abs = 0.0
    for key in ref.files:
        scenario, seed = key.split("_seed")
        tr = synthetic_trace(scenario, T=120.0, dt=0.1, seed=int(seed))
        expected = ref[key]
        assert tr.d.shape == expected.shape
        np.testing.assert_allclose(tr.d, expected, rtol=1e-12, atol=1e-9)
        worst_abs = max(worst_abs, float(np.max(np.abs(tr.d - expected))))
    assert worst_abs < 1e-9


def test_reference_covers_all_three_memo_scenarios():
    keys = np.load(REF).files
    assert {k.split("_seed")[0] for k in keys} == {"A", "B", "C"}
