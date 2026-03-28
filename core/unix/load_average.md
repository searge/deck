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

The kernel uses an exponentially decaying formula for each window:

$$
\text{LA}_{t} = \text{LA}_{t-1} \cdot e^{-t/T} + n \cdot \left(1 - e^{-t/T}\right)
$$

| Symbol | Meaning |
|--------|---------|
| \(t\) | sampling interval — 5 seconds |
| \(T\) | window size — 60 s / 300 s / 900 s for 1 / 5 / 15 min |
| \(n\) | number of processes in run queue at sample time |

In practice you never compute this by hand — the kernel does it.
What matters is **interpretation**.

## Interpreting the Numbers

A single LA value is meaningless without knowing the CPU count.
**Always check `nproc` first.**

$$
\text{LA}_{\text{norm}} = \frac{\text{LA}}{\text{nCPU}}
$$

| Normalized LA | State |
|:---:|---|
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
|---|---|---|
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
# or
cat /proc/loadavg

# 2. Check CPU count
nproc

# 3. If LA_norm > 1.0 — find out why
# CPU bound?
top        # look at %CPU column, check for R-state processes
mpstat 1

# I/O bound? (Linux only)
iostat -x 1
vmstat 1   # look at 'b' column (blocked) and 'wa' (iowait)

# Which processes are in D state?
ps aux | awk '$8 ~ /^D/ { print }'
```

## Quick Reference

```bash
uptime                     # LA 1/5/15 min
cat /proc/loadavg          # same + running/total processes + last PID
nproc                      # logical CPU count
nproc --all                # all CPUs including offline
lscpu | grep "^CPU(s):"    # same
grep -c processor /proc/cpuinfo  # same, works everywhere
```
