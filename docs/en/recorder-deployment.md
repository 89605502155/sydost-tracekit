# Recorder deployment

The guest recorder is one Python file with the standard library only:
`src/sydost_tracekit/recorder.py`. It runs on Python 3.8 or newer and reads the Linux procfs.

## Steps

1. Copy the file into the guest, for example to `/opt/tracekit/recorder.py`.
2. Check that a sample can be taken, for example with a 1-second recording:

```sh
python3 /opt/tracekit/recorder.py --hz 10 --duration 1 --out /tmp/check.csv
```

3. Run it for the whole experiment. It writes `<out>.csv` and `<out>.csv.json`
   (the summary: samples, late and skipped ticks, CPU share).

## Systemd unit

```ini
[Unit]
Description=sydost-tracekit guest memory recorder
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 /opt/tracekit/recorder.py --hz 10 --duration 7200 --out /var/lib/tracekit/trace.csv
Restart=no
Nice=19
CPUAccounting=yes

[Install]
WantedBy=multi-user.target
```

Create the directory `/var/lib/tracekit` first. Start the unit with `systemctl start`
when the load starts; the duration limits the recording.

## What the summary means

- `late`: ticks whose sample began more than half a period after the due time.
- `skipped`: ticks dropped because the recorder was behind by a whole period or more.
  Skipped ticks are not written, so the time grid has gaps; the reconstruction in
  `recordings_to_trace` bridges them.
- `cpu_share`: CPU time of the recorder divided by its wall time. Measure it at the planned
  frequency before a long run. The tests do not measure overhead.

## Clock

Synchronise the guest clock (for example chrony) before the run. Host and guest times are
compared through `t_real_s`; the error of the alignment is given by `estimate_offset`.
