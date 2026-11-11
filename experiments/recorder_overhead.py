"""HEAVY: CPU share, late and skipped ticks of the guest recorder at several frequencies.

Run inside a guest, one frequency after another, each for --duration seconds:

    python3 experiments/recorder_overhead.py --hz 1,10,100 --duration 1800

Expected runtime: about 3 x 30 min at the default duration, about 15 MiB of memory.
Not run by the tests; the results go to --out (CSV).
"""

from __future__ import annotations

import argparse
import csv
import tempfile
from pathlib import Path

from sydost_tracekit.recorder import record


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hz", default="1,10,100", help="frequencies, Hz")
    ap.add_argument("--duration", type=float, default=1800.0, help="length of each run, s")
    ap.add_argument("--out", default="recorder_overhead.csv")
    args = ap.parse_args()
    rows = []
    for hz in (float(x) for x in args.hz.split(",")):
        tmp = Path(tempfile.mkdtemp()) / "trace.csv"
        summary = record(str(tmp), hz=hz, duration=args.duration)
        rows.append(
            {
                k: summary[k]
                for k in ("hz", "samples", "late", "skipped", "max_lag_s", "cpu_share", "wall_s")
            }
        )
        print(rows[-1])
    with Path(args.out).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
