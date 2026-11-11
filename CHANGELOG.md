# Changelog

All notable changes of sydost-tracekit are documented here. The project follows
[Semantic Versioning](https://semver.org).

## [0.0.1] — 2026-11-11

First release: reference memory traces of virtual machines and the accuracy of the
accumulated-deficit estimate from samples (A. Ferubko, O. Kazakov, BGITU).

* Recorder: the tick after a sample is the first one not behind by a whole period; an overdue
  tick is run once, a tick is never sampled twice.
* `synthetic`: scenarios A, B, C reproduce the prototype arrays bit for bit; held-out scenario D.

* `recorder`: the guest recorder, Python standard library only, one file; drift-free
  schedule, late and skipped tick accounting, CPU share of the recorder.
* `collector`: host collector of libvirt memory statistics with the snapshot age
  (optional extra `kvm`, imported lazily).
* `Trace`, `load_trace`, `save_trace`, `TraceFormatError`: the trace format with validation;
  `recordings_to_trace` and `demand` (balloon-aware) for recordings.
* `clock`: host and guest clock alignment (Cristian's algorithm) and drift in ppm.
* `integral`: deficit, its estimate from samples, `positive_part_integral` (exact, crossing
  points), `sampling_study`.
* `bounds`: statement 4.1 (`hold_error_bound`), the refined hold bound
  (`hold_error_bounds_refined`), statement 4.2 (`linear_error_bound`), `estimate_constants`,
  `plan_sampling` (the sampling rate for a target error).
* `replay`, `tune`: controller replay with fixed polling, Pareto front and selection under
  `P(θ) ≤ α` and `D ≤ D_max`.
* Command line `sydost-tracekit record | integrate | bound | tune`.
* Documentation in English and Russian, seven examples, tests with coverage.
