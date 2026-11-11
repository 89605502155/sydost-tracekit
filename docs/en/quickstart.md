# Quickstart

Install the package, then estimate the accumulated deficit of a trace from samples.

```sh
pip install sydost-tracekit
```

The first example takes a synthetic trace (scenario A, four machines), replays a
controller polled every 4 seconds, and estimates the deficit from samples every 2 seconds:

```python
from sydost_tracekit import deficit_integral, estimate_from_samples, simulate, synthetic_trace

tr = synthetic_trace("A", T=600.0, dt=0.1, seed=7)  # reference trace, step 0.1 s
run = simulate(tr, interval_s=4.0)  # allocation of a controller polled every 4 s
D = deficit_integral(tr.d, run.alloc, tr.dt)
est = estimate_from_samples(tr.t[::20], tr.d[:, ::20], run.alloc, tr.dt, "linear")
print(f"D = {D:.1f} MiB*s, linear estimate from 2 s samples = {est:.1f} MiB*s")
```

Next steps:

- [Trace format](trace-format.md): how the demand of a machine is stored.
- [Bounds](bounds.md): how large the error of the estimate can be, and which sampling rate is needed.
- [Recorder deployment](recorder-deployment.md): how to run the guest recorder.
- [CLI](cli.md) and [API](api.md).

The examples in [examples](../../examples/) show each function on a short script.
