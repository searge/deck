---
title: Roadmap — Unix / Math
description: Learning path through the mathematics hidden inside Unix/Linux internals.
---

# Roadmap — Unix / Math

Sequential exploration of the mathematics hidden inside Unix/Linux.
Each topic produces a script in `scripts/unix/` and a note in `core/unix/math/`.

## Progress

### Phase 1 — Signal & Time ✓

Foundation: how the kernel tracks state over time.

- [x] **EWMA** — load average, exponential decay, run queue simulation
  - script: `scripts/unix/ewma.py`
  - note: `core/unix/math/ewma.md`
  - math: exponential decay, weighted averages, Poisson arrivals

---

### Phase 2 — Probability & Noise

Randomness that the kernel depends on.

- [ ] **Poisson arrivals** — why `rng.poisson()` is the right model for syscalls and packets
  - math: Poisson distribution, arrival rate λ, inter-arrival times
- [ ] **Entropy & /dev/urandom** — how the kernel collects entropy, CSPRNG internals
  - math: Shannon entropy H(X) = −Σ p log p, uniform distribution, hash mixing

---

### Phase 3 — Scheduling

How the kernel and platform control planes decide where work runs next.

- [x] **Simulated annealing** — workload placement across constrained nodes
  - script: `scripts/unix/simulated_annealing.py`
  - note: `core/unix/math/simulated_annealing.md`
  - math: stochastic optimization, Metropolis acceptance, geometric cooling
- [ ] **CFS virtual runtime** — Completely Fair Scheduler, weight-based time slices
  - math: logarithmic functions, priority queues, fairness (min-max)
- [ ] **Queueing theory** — M/M/1, M/D/1: latency, throughput, utilisation
  - math: Little's law L = λW, utilisation ρ = λ/μ, response time

---

### Phase 4 — Networking

Mathematics inside TCP/IP.

- [ ] **TCP CUBIC** — congestion window growth and recovery after packet loss
  - math: cubic function W(t) = C(t − K)³ + W_max, AIMD
- [ ] **Checksums & CRC** — data integrity from simple sums to polynomial division
  - math: modular arithmetic, polynomial division over GF(2)

---

### Phase 5 — Storage

Filesystem and memory internals.

- [ ] **Inode B-tree** — how ext4/btrfs find a file in O(log n)
  - math: B-tree fanout, search depth, amortised cost
- [ ] **Buddy allocator** — how the kernel splits and merges memory pages
  - math: powers of 2, binary tree, internal fragmentation

---

### Phase 6 — Permissions & Masks

Bit-level arithmetic in Unix.

- [ ] **chmod bitmask** — `755` decoded: AND/OR/XOR across 9 permission bits
  - math: boolean algebra, bitwise operations, set theory (rwx as a set)

---

## Dependency map

```text
EWMA
 └─► Poisson ──► CFS ──► Queueing ──► TCP CUBIC
       └─► Entropy           └─► CRC
              └─► Annealing
                        └─► B-tree ──► Buddy
                              └─► chmod (bitmask)
```

Topics flow left-to-right: each one builds on the intuition of the previous.
