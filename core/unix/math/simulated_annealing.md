---
title: Simulated Annealing
tags:
  - unix
  - math
  - optimization
  - kubernetes
aliases:
  - Annealing
description: >-
  Stochastic optimization through temperature, controlled exploration, and
  workload placement.
---

# Simulated Annealing

Simulated annealing searches for a low-cost solution without getting trapped at
the first local minimum. It sometimes accepts a worse move while the system is
"hot", then becomes increasingly conservative as it cools.

This lab applies the algorithm to **workload placement**: assign connected
services to cluster nodes while respecting CPU and memory capacity, balancing
utilization, reducing network distance, and spreading replicas.

> [!info] Model, not kube-scheduler internals
> Kubernetes filters infeasible nodes and scores the feasible candidates for
> each unscheduled Pod. This lab searches complete cluster placements and may
> revisit earlier decisions. It is closer to offline capacity planning or a
> descheduler experiment than to the default scheduler's hot path.

## Why Greedy Gets Stuck

With (m) nodes and (w) workloads, there are:

$$
m^w
$$

possible placements before constraints are considered. The lab has four nodes
and eight workloads, so its full space contains (4^8 = 65,536) assignments.
That is small enough to understand, but the same formulation grows
exponentially.

A greedy algorithm can place the largest workload on the least-loaded node at
each step. The result may be balanced, but moving one service closer to its
database can temporarily make balance worse. Hill climbing rejects that move
and cannot cross the higher-cost state to reach a better arrangement.

## Energy Function

Annealing requires one scalar objective, conventionally called **energy**:

$$
E(x) = w_c C(x) + w_b B(x) + w_n N(x) + w_s S(x)
$$

| Component | Meaning |
| --------- | ------- |
| (C(x)) | Squared CPU and memory capacity violations |
| (B(x)) | Squared deviation from cluster-wide target utilization |
| (N(x)) | Traffic rate multiplied by node or zone distance |
| (S(x)) | Same-node and same-zone replica penalties |

The units are deliberately artificial. Only relative scores matter. A capacity
weight of `10_000` makes an overloaded node far more expensive than a moderate
network or balance improvement.

> [!warning] The objective is the policy
> The optimizer cannot tell whether the score represents the real operational
> goal. Bad weights produce a precisely optimized bad placement.

## Accepting a Worse Move

Let a candidate change the energy by:

$$
\Delta E = E_{candidate} - E_{current}
$$

An improvement has (Delta E \le 0) and is always accepted. A worse move is
accepted with the Metropolis probability:

$$
P(accept) = e^{-\Delta E / T}
$$

At high temperature (T), the exponent is close to zero and exploration is
common. At low temperature, even a small increase becomes unlikely.

For example, a move that adds 20 energy has these probabilities:

| Temperature | Probability |
| :---------: | :---------: |
| 100 | 81.9% |
| 20 | 36.8% |
| 5 | 1.8% |

## Cooling Schedule

The lab uses geometric cooling:

$$
T_k = T_0 \alpha^k
$$

with (T_0 = 80), (alpha = 0.998), and 5,000 steps. A larger
(alpha) cools more slowly and explores longer; a smaller value converges
faster but behaves more like hill climbing.

```python
from math import exp


def acceptance_probability(delta_energy: float, temperature: float) -> float:
    if delta_energy <= 0:
        return 1.0
    return exp(-delta_energy / temperature)
```

## Algorithm

```text
current = random feasible placement
best = current

for each temperature:
    candidate = move one workload to another node
    delta = energy(candidate) - energy(current)

    if delta <= 0 or random() < exp(-delta / temperature):
        current = candidate

    best = min(best, current)
    temperature *= cooling_rate

return best
```

`current` and `best` are different on purpose. Annealing may leave a good state
to keep exploring, so the algorithm must remember the best state seen across
the entire run.

## Run the Lab

The implementation lives in `scripts/unix/simulated_annealing.py`. It uses a
fixed random seed, so the default run is reproducible.

```bash
# Print baseline scores and the best placement
uv run python scripts/unix/simulated_annealing.py

# Also write an interactive convergence report
uv run python scripts/unix/simulated_annealing.py \
  --html /tmp/simulated_annealing.html
```

The report compares three placements:

- **random:** a feasible but unoptimized starting point;
- **greedy:** largest request first, least-loaded feasible node;
- **annealed:** best state observed during stochastic exploration.

With the default seed, their total energies are `149.72`, `127.72`, and `77.97`
respectively. The annealed placement has no capacity or replica-spread penalty;
its remaining cost is the balance-versus-network trade-off.

Exhaustive enumeration is still possible for this toy scenario: 21,408 of the
65,536 assignments are feasible, and `77.96875` is the global minimum. There
are 32 equivalent optima caused by node symmetry; annealing finds one of them.

The Plotly report shows current versus best energy, temperature decay,
objective components, and final CPU/memory utilization per node.

## Reading the Trace

Early in the run, current energy should oscillate as worse moves are accepted.
Best energy can only stay flat or decrease. Near the end, current energy should
settle close to the best value as temperature approaches zero.

| Symptom | Likely cause | Adjustment |
| ------- | ------------ | ---------- |
| Random walk until the end | Temperature too high | Lower \(T_0\) or \(\alpha\) |
| Stops improving immediately | Temperature too low | Raise \(T_0\) |
| Finds different weak minima | Cooling too fast | Raise \(\alpha\) or steps |
| "Optimal" but unusable | Incomplete objective | Add constraints or retune weights |
| Most time scoring | Expensive objective | Cache incremental score changes |

Enumeration proves optimality for this small lab, not for a realistic cluster.
There, use several seeds, compare against a simple baseline, and verify all hard
constraints independently.

## Where It Fits

Simulated annealing is useful when:

- the search space is discrete and too large for exhaustive search;
- a candidate can be changed locally with a cheap neighbor operation;
- solution quality is measurable even when no gradient exists;
- a good solution is enough and an exact optimum is too expensive.

For platform engineering, plausible applications include offline workload
placement, maintenance-window planning, shard allocation, CI job packing, and
topology redesign. For online per-Pod scheduling, predictable latency and hard
filtering are usually more important than long stochastic exploration.

## References

- [Optimization by Simulated Annealing](https://doi.org/10.1126/science.220.4598.671)
- [Kubernetes Scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/)
- [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
