# sydost-tracekit

[Русская версия](README.ru.md) · [Documentation](docs/en/quickstart.md) · [Changelog](CHANGELOG.md)

`sydost-tracekit` records reference memory traces of virtual machines, estimates the
accumulated memory deficit from samples taken at a coarser step, bounds the error of
that estimate, and tunes the monitoring configuration on the traces.

The accumulated deficit `D = ∫ (d − a)⁺ dt` is an integral. Samples of the demand held
for a step ℓ define a simple function, so the estimate converges to `D` as ℓ → 0.
The library gives explicit error bounds: `ℓ·V(d)` for holding the samples (first order)
and `ℓ²·(T·M/12 + K·L/3)` for linear interpolation (second order).

Developed at Bryansk State Engineering-Technological University (BGITU) by Andrey Ferubko
([ORCID](https://orcid.org/0009-0006-5625-137X)) and Oleg Kazakov
([ORCID](https://orcid.org/0000-0001-9665-8138)).

## Install

```sh
pip install sydost-tracekit           # analysis, bounds, tuning, CLI
pip install "sydost-tracekit[kvm]"    # adds libvirt-python for the host collector
uv add sydost-tracekit
```

The guest recorder needs only the Python standard library: copy the single file
`src/sydost_tracekit/recorder.py` into the guest (see the deployment guide).

## Quickstart

```python
from sydost_tracekit import deficit_integral, estimate_from_samples, simulate, synthetic_trace

tr = synthetic_trace("A", T=600.0, dt=0.1, seed=7)  # reference trace, step 0.1 s
run = simulate(tr, interval_s=4.0)  # allocation of a controller polled every 4 s
D = deficit_integral(tr.d, run.alloc, tr.dt)
est = estimate_from_samples(tr.t[::20], tr.d[:, ::20], run.alloc, tr.dt, "linear")
print(f"D = {D:.1f} MiB*s, linear estimate from 2 s samples = {est:.1f} MiB*s")
```

## Command line

```sh
sydost-tracekit record --hz 10 --duration 600 --out trace_vm1.csv   # run the recorder here
sydost-tracekit integrate ref.csv --alloc alloc.csv --steps 0.5,1,2 # estimate D from samples
sydost-tracekit bound ref.csv --steps 1 --target 1e4               # bounds and sampling rate
sydost-tracekit tune train.csv --intervals 1,2,4,8 --alpha 0.5 --dmax 10
```

## Features

- **Sampling rate for a target error.** `plan_sampling` gives the method and the step
  (rate) for which the a-priori bound does not exceed the target, from the constants of
  a reference trace.
- **Refined hold bound.** `hold_error_bounds_refined` counts only the variation that
  matters for the deficit (the rises above the allocation and the falls of the held
  value above it). It is valid and tighter than `ℓ·V(d)`; the examples show it.
- **Exact integral of the positive part** of a piecewise linear signal via the crossing
  points (`positive_part_integral`); a step allocation is a repeated knot.
- **Guest recorder** in the standard library only: drift-free schedule, late and skipped
  tick accounting, CPU share of the recorder itself.
- **Host–guest clock alignment**: offset from request–response exchanges (Cristian's
  algorithm, the error is at most half of the round trip) and linear drift in ppm.
- **Trace format** with validation (uniform grid, finite values, unique names).
- **Tuner**: sweep of configurations, Pareto front, selection under `P(θ) ≤ α` and
  `D ≤ D_max`.

## How it differs from generic tools

| Need | Generic tools | sydost-tracekit |
|---|---|---|
| Integral of a sampled series | `scipy.integrate.trapezoid`, `pandas` resampling | the integral of the **deficit** `(d − a)⁺` with a known allocation, and the exact crossing-point formula |
| Error of the integral | none: no bound for a sampled deficit | explicit bounds `ℓ·V(d)`, `ℓ²(T·M/12 + K·L/3)` and the refined hold bound |
| "What sampling rate do I need?" | rule of thumb | the step for a target absolute error, from the trace |
| Collection | Prometheus, node_exporter, collectd: sample every 15–60 s by default | a stdlib guest recorder at 10 Hz with overhead accounting, and a libvirt host collector |
| Tuning | manual thresholds | Pareto front over monitoring cost, selection under constraints |

## Documentation

- English: [quickstart](docs/en/quickstart.md), [trace format](docs/en/trace-format.md),
  [bounds and theory](docs/en/bounds.md), [recorder deployment](docs/en/recorder-deployment.md),
  [API](docs/en/api.md), [CLI](docs/en/cli.md).
- Русский: [README.ru.md](README.ru.md), [docs/ru](docs/ru).

Runnable scripts are in [examples](examples/); they finish in a few seconds.

## Development

```sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```

Enable the commit-message rule once per clone: `git config core.hooksPath scripts/git-hooks`.
Heavy experiments (minutes of recording at 100 Hz) are in [experiments](experiments/), not run by the tests.

## Citation

See [CITATION.cff](CITATION.cff). Authors: Andrey Ferubko (ferubko1999@yandex.ru) and
Oleg Kazakov (kazakov@bgitu.ru), Bryansk State Engineering-Technological University (BGITU).

## License

MIT, see [LICENSE](LICENSE). Copyright (c) 2026 Andrey Ferubko, Oleg Kazakov.
