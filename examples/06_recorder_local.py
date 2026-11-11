"""Run the guest recorder on this machine for one second (Linux procfs)."""

import os
import tempfile

from sydost_tracekit.recorder import record

out = os.path.join(tempfile.mkdtemp(), "trace.csv")
summary = record(out, hz=10.0, duration=1.0)
print(f"{summary['samples']} samples, {summary['late']} late, cpu share {summary['cpu_share']:.4f}")
