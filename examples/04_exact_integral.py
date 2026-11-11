"""Exact integral of the positive part of a piecewise linear signal (crossing points)."""

import numpy as np

from sydost_tracekit import positive_part_integral

t = np.array([0.0, 1.0, 2.0])
x = np.array([0.0, 4.0, 0.0])  # demand rises above the allocation and falls back
a = np.array([2.0, 2.0, 2.0])
print(positive_part_integral(t, x, a))  # two triangles of area 0.5 each
