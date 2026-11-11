"""Reference memory traces of virtual machines and accuracy of accumulated-deficit estimates.

Modules
-------
recorder
    Guest recorder, Python standard library only; copied into a guest as one file.
collector
    Host collector of libvirt memory statistics (optional extra ``kvm``).
trace
    Trace of demand on a uniform grid, CSV format with validation.
load
    Recordings of the guest recorder turned into traces.
clock
    Host and guest clock alignment (Cristian's algorithm, drift).
reconstruct
    Hold and linear reconstruction between samples.
integral
    Accumulated deficit, its estimate from samples, exact positive-part integral.
bounds
    A-priori bounds (hold, linear), the refined hold bound, the sampling plan.
replay, tune
    Replay of a controller on a trace, Pareto front and selection under constraints.
synthetic
    Synthetic scenarios A, B, C for debugging.
cli
    Command line ``sydost-tracekit``.
"""

from .bounds import (
    Constants,
    Plan,
    estimate_constants,
    hold_error_bound,
    hold_error_bounds_refined,
    linear_error_bound,
    plan_sampling,
    required_step,
)
from .clock import ClockOffset, ClockSample, estimate_offset, fit_drift, guest_to_host
from .integral import (
    deficit,
    deficit_integral,
    estimate_from_samples,
    positive_part_integral,
    sampling_study,
    total_variation,
)
from .load import demand, read_recorder_csv, recordings_to_trace
from .reconstruct import hold, linear
from .replay import ReserveController, RunResult, simulate
from .synthetic import SCENARIOS, VmProfile, synthetic_trace
from .trace import Trace, TraceFormatError, load_trace, save_trace
from .tune import pareto_front, select, sweep

__version__ = "0.0.1"

__all__ = [
    "SCENARIOS",
    "ClockOffset",
    "ClockSample",
    "Constants",
    "Plan",
    "ReserveController",
    "RunResult",
    "Trace",
    "TraceFormatError",
    "VmProfile",
    "__version__",
    "deficit",
    "deficit_integral",
    "demand",
    "estimate_constants",
    "estimate_from_samples",
    "estimate_offset",
    "fit_drift",
    "guest_to_host",
    "hold",
    "hold_error_bound",
    "hold_error_bounds_refined",
    "linear",
    "linear_error_bound",
    "load_trace",
    "pareto_front",
    "plan_sampling",
    "positive_part_integral",
    "read_recorder_csv",
    "recordings_to_trace",
    "required_step",
    "sampling_study",
    "save_trace",
    "select",
    "simulate",
    "sweep",
    "synthetic_trace",
    "total_variation",
]
