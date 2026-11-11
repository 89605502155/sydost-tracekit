# API

The public names are exported from `sydost_tracekit`. Each function has a numpy-style
docstring with runnable examples.

| Group | Names | Purpose |
|---|---|---|
| Traces | `Trace`, `load_trace`, `save_trace`, `TraceFormatError` | trace on a uniform grid, CSV format |
| Recordings | `read_recorder_csv`, `demand`, `recordings_to_trace` | recorder output to traces |
| Clocks | `ClockSample`, `estimate_offset`, `guest_to_host`, `fit_drift` | host–guest alignment |
| Reconstruction | `hold`, `linear` | samples to a function of time |
| Integral | `deficit`, `deficit_integral`, `total_variation`, `positive_part_integral`, `estimate_from_samples`, `sampling_study` | deficit and its estimate |
| Bounds | `hold_error_bound`, `hold_error_bounds_refined`, `linear_error_bound`, `estimate_constants`, `Constants`, `required_step`, `plan_sampling`, `Plan` | a-priori and refined bounds, sampling plan |
| Replay | `ReserveController`, `simulate`, `RunResult` | controller replay with fixed polling |
| Tuning | `sweep`, `pareto_front`, `select` | cost–quality front and selection |
| Synthetic | `synthetic_trace`, `VmProfile`, `SCENARIOS` | scenarios A, B, C (identical to the prototype for the same seed); D held out |
| Guest | `sydost_tracekit.recorder.record`, `main` | stdlib recorder (also the file copied to guests) |
| Host | `sydost_tracekit.collector.collect`, `connect` | libvirt collector (extra `kvm`) |

Units: time in seconds, memory in MiB, the accumulated deficit in MiB·s (the CLI prints GiB·s
where the name says so).
