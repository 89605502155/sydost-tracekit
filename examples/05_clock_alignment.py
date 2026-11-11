"""Host and guest clocks: offset from request-response exchanges."""

from sydost_tracekit import ClockSample, estimate_offset

samples = [
    ClockSample(t_send_host=100.0, t_guest=105.3, t_recv_host=100.4),
    ClockSample(t_send_host=200.0, t_guest=205.1, t_recv_host=200.3),
]
est = estimate_offset(samples)  # the exchange with the shortest round trip is used
print(f"offset guest - host = {est.offset_s:.2f} s, error at most {est.uncertainty_s:.2f} s")
