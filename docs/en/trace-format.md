# Trace format

A trace is the demand `d[i, k]` of virtual machine `i` at the moment `k·dt`, in MiB.
Time is in seconds. The demand of a machine comes from its guest:

    d = (MemTotal − MemAvailable) / 1024 + reserve            [MiB]

## CSV file

The header is `t_s,<name1>,<name2>,...`, one row per grid point:

```text
t_s,vm1,vm2
0.000000,1024.000,2048.500
0.100000,1024.300,2048.500
```

- The first column is `t_s` and the grid is uniform: consecutive times differ by `dt`,
  up to rounding (the tolerance is the larger of 1e-6 s and 1e-3·dt).
- Values are finite numbers; empty values and NaN are rejected.
- Names are unique and contain no commas.
- `<file>.json` (optional) holds the metadata: `dt`, `names` and any extra fields
  (scenario, seed, method, source). It is written by `save_trace` and read by `load_trace`.

```python
from sydost_tracekit import Trace, load_trace, save_trace

tr = Trace(0.5, [[1.0, 2.0, 3.0]], ["vm1"])
save_trace(tr, "trace.csv")
print(load_trace("trace.csv").names)
```

## Recordings

The guest recorder writes one CSV per machine with the columns `t_mono_s`, `t_real_s`,
`mem_total_kib`, `mem_free_kib`, `mem_available_kib`, `cached_kib`, `swap_total_kib`,
`swap_free_kib`, `balloon_kib`, `psi_some_total_us`, `psi_full_total_us`, `pgmajfault`,
`pswpin`, `pswpout`, `oom_kill`. An empty value means that the source is missing (for
example, no pressure file or no `Balloon` line in `/proc/meminfo`).

`recordings_to_trace` turns the recordings of several machines into one trace on a common
time span, with linear or hold reconstruction between the recorded rows.

## Balloon

With `autodeflate` enabled for the memory balloon, the guest kernel already lowers
`MemTotal` by the balloon size. Pass `autodeflate=True` to subtract the balloon once more
in `demand`; the balloon size comes from the `balloon_kib` column or from `balloon_mib`.
Without `autodeflate` the balloon is not subtracted.

## Clocks

The time column `t_real_s` is comparable between machines only after the clocks are
aligned (see the clock helpers in the API). `t_mono_s` is valid only inside one machine.
