# Command line

`sydost-tracekit` has four commands. Each has `--help`.

## record

Runs the guest recorder on this machine. It writes the CSV and the JSON summary.

```sh
sydost-tracekit record --hz 10 --duration 600 --out trace_vm1.csv
```

## integrate

Estimates the deficit from samples of a reference trace for several steps and methods.
The allocation file has the same format and grid as the reference.

```sh
sydost-tracekit integrate ref.csv --alloc alloc.csv --steps 0.5,1,2 --methods hold,linear
```

The output gives the exact `D` and the relative error in percent for each step and method.

## bound

Prints the constants of the reference trace (`V`, `L`, `M`, `K`), the linear bound and the
hold bound `ℓ·V` for the steps given, and, with `--target`, the method, step and rate that
meet an absolute error in MiB·s.

```sh
sydost-tracekit bound ref.csv --steps 1,2 --target 10000
```

## tune

Replays fixed polling intervals on the trace, prints the cost (samples per machine-hour),
`P(θ)`, `D`, the Pareto flag, and the selected interval under `P ≤ α` and `D ≤ D_max`.

```sh
sydost-tracekit tune train.csv --intervals 1,2,4,8 --theta 64 --alpha 0.5 --dmax 10
```

`--theta` is the deficit threshold in MiB. `--dmax` is in GiB·s. Without `--dmax` there is no
limit on `D`. If no interval satisfies the constraints, the command says so.
