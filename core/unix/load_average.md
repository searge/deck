---
title: Load Average
tags:
  - linux
  - unix
  - performance
  - interview
---

# Load Average

Load average is an **exponentially weighted moving average** of the run queue
length, sampled every 5 seconds and reported for 1, 5, and 15-minute windows.

```bash
$ uptime
 12:34:56 up 7 days,  3:21,  2 users,  load average: 2.45, 1.80, 1.20
                                                       ^^^^  ^^^^  ^^^^
                                                       1min  5min  15min
```

## How It Is Calculated

The kernel uses an [exponentially weighted moving average](math/ewma.md) —
updated every 5 seconds, one value per window. In practice you never compute
this by hand. What matters is **interpretation**.

## Interpreting the Numbers

A single LA value is meaningless without knowing the CPU count.
**Always check `nproc` first.**

$$
\text{LA}_{\text{norm}} = \frac{\text{LA}}{\text{nCPU}}
$$

| Normalized LA | State |
| :---: | --- |
| \(< 0.7\) | Healthy — headroom available |
| \(\approx 1.0\) | Saturated — fully loaded, no slack |
| \(> 1.0\) | Overloaded — processes waiting |

```bash
# Get CPU count
nproc

# Example: LA = 6.0, nCPU = 4
# LA_norm = 6.0 / 4 = 1.5  →  overloaded
```

## Linux vs BSD / macOS

This is where the platforms diverge:

| | Linux | BSD / macOS |
| --- | --- | --- |
| Run queue (R state) | ✅ included | ✅ included |
| Uninterruptible sleep (D state) | ✅ included | ❌ not included |
| I/O wait inflates LA | yes | no |

**Linux** counts processes blocked on I/O (`D` state — disk, NFS, etc.)
as part of the load. High LA on Linux may indicate an **I/O bottleneck**,
not a CPU one.

**BSD / macOS** only counts processes that actively want CPU time.
High LA there is more directly a signal of **CPU saturation**.

> [!warning] Interview trap
> If you see `LA: 6 8 5` on a Linux box — don't say "8 CPUs are busy."
> Ask: **how many CPUs does the machine have?** And: is this I/O load or CPU load?

## Diagnosis Workflow

```bash
# 1. Check LA
uptime
cat /proc/loadavg

# 2. Check CPU count — without this the numbers mean nothing
nproc
```

If `LA / nCPU > 1.0`, the machine is overloaded. Next question: **why?**

### CPU-bound

Processes actively consuming CPU cycles — `%us` + `%sy` is high,
`%wa` is low.

```bash
# Overall CPU breakdown — look for high %us (user) or %sy (system)
mpstat 1

# Which processes are burning CPU?
top        # sort by %CPU, watch for R-state in the S column
pidstat 1  # per-process CPU usage over time

# Count processes currently running or waiting for CPU
ps aux | awk '$8 == "R" { count++ } END { print count " running" }'
```

**Fix direction:** profile the application, optimise hot paths,
scale horizontally, or add CPU cores.

### I/O-bound (Linux only)

Processes blocked waiting for disk or network I/O — stuck in `D` state
(uninterruptible sleep). LA is high but `%wa` is elevated, not `%us`.

```bash
# CPU iowait — if %wa is consistently > 10–20 %, suspect I/O
vmstat 1   # 'wa' column: CPU time spent waiting for I/O
           # 'b'  column: processes blocked on I/O right now

# Which disks are saturated?
iostat -x 1   # %util → 100 % means the device is the bottleneck
              # await → average I/O latency in ms

# Which processes are stuck in D state?
ps aux | awk '$8 ~ /^D/ { print $0 }'

# Continuous watch for D-state processes
watch -n 1 "ps aux | awk '\$8 ~ /^D/'"
```

**Fix direction:** faster storage, reduce fsync calls, add caching,
check for NFS hangs or network-backed mounts.

> [!tip] CPU-bound vs I/O-bound — quick rule
>
> ```text
> high LA + low %wa  →  CPU-bound
> high LA + high %wa →  I/O-bound (Linux only)
> ```
>
> On BSD / macOS the distinction is simpler: high LA always means CPU pressure.

## Parallel Fleet Snapshot

The repository includes equivalent Python and Bash implementations of the
diagnosis workflow for a list of SSH hosts:

- [`la_iowait.py`](https://github.com/searge/deck/blob/main/scripts/unix/la_iowait.py)
  uses one `asyncio` task per host and passes results through an
  `asyncio.Queue`;
- [`la_iowait.sh`](https://github.com/searge/deck/blob/main/scripts/unix/la_iowait.sh)
  uses background jobs and a FIFO, applying the pattern from
  [Bash Parallel](hacks/bash/parallel.md).

The input file contains one SSH host or `~/.ssh/config` alias per line. Blank
lines and lines beginning with `#` are ignored.

```text title="servers.txt"
runner-01
runner-02
# runner-maintenance
```

```bash
# Default: sort by 5-minute load average
uv run python scripts/unix/la_iowait.py servers.txt

# Other Python sort keys: la1, la15, cpu, iowait, r, b
uv run python scripts/unix/la_iowait.py servers.txt iowait

# Bash version always sorts by la5
bash scripts/unix/la_iowait.sh servers.txt
```

Both versions honor `SSH_USER` and `SSH_KEY`; otherwise `ssh` uses its normal
configuration and agent. Remote Linux hosts need `nproc`, `vmstat`, and `awk`.
The `state` column is based on `la1 / nproc`, while the default `la5` ordering
keeps short spikes from dominating the list.

## Quick Reference

```bash
uptime                     # LA 1/5/15 min
cat /proc/loadavg          # same + running/total processes + last PID
nproc                      # logical CPU count
nproc --all                # all CPUs including offline
lscpu | grep "^CPU(s):"    # same
grep -c processor /proc/cpuinfo  # same, works everywhere
```
