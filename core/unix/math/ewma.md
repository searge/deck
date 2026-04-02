---
title: Exponential Weighted Moving Average
tags:
  - linux
  - math
  - performance
  - interview
---

# Exponential Weighted Moving Average

## The Problem

The kernel needs a single number that answers: *how loaded was this machine
recently?* A naive approach — store the last 300 samples and divide — wastes
memory and produces jarring jumps when an old spike drops off the window edge.

EWMA solves both: **O(1) memory, O(1) compute, smooth response.**

## The Formula

$$
\text{LA}_{t} = \text{LA}_{t-1} \cdot e^{-\Delta t / T} + n \cdot \left(1 - e^{-\Delta t / T}\right)
$$

| Symbol | Meaning |
|--------|---------|
| \(\Delta t\) | sampling interval — 5 s |
| \(T\) | window size — 60 / 300 / 900 s for 1 / 5 / 15 min |
| \(n\) | run queue length at sample time |
| \(e^{-\Delta t / T}\) | decay factor — weight of the past |

The decay factor \(\alpha = e^{-\Delta t / T}\) is why Euler's number appears:
it is the only function whose rate of forgetting is proportional to what
remains — a natural fit for a memory that fades continuously, not in steps.

## Python

Direct translation of the formula — nothing more:

```python
from math import exp

SAMPLE_INTERVAL_SECONDS = 5


def decay_factor(window_seconds: int) -> float:
    return exp(-SAMPLE_INTERVAL_SECONDS / window_seconds)


def next_load(
    previous_load: float,
    runnable_processes: int,
    window_seconds: int,
) -> float:
    alpha = decay_factor(window_seconds)
    return previous_load * alpha + runnable_processes * (1 - alpha)
```

For a full simulation with realistic process data and plots,
see `scripts/unix/ewma.py` in the repository root.

## Decay Factor by Window

Each window "forgets" the past at a different rate:

$$
\alpha = e^{-5/T}
$$

| Window | \(T\) | \(\alpha\) | Present weight | Half-life |
|--------|-------|-----------|----------------|-----------|
| 1 min  | 60 s  | ≈ 0.9200  | 8.0 % | ~43 s |
| 5 min  | 300 s | ≈ 0.9835  | 1.6 % | ~3.6 min |
| 15 min | 900 s | ≈ 0.9945  | 0.6 % | ~10.4 min |

A spike in the run queue affects the **1-minute window immediately** but
takes over 10 minutes to fully show in the 15-minute average.

## Where This Lives in Linux

The kernel updates all three windows in `calc_load()` inside
`kernel/sched/loadavg.c`, called from the `TIMER_SOFTIRQ` every 5 seconds.
The constants are precomputed as fixed-point integers to avoid floating-point
arithmetic in interrupt context.
