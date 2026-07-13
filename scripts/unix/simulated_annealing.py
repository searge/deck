#!/usr/bin/env python3
# %%
"""Simulated annealing lab: multi-resource workload placement.

Places a small set of connected workloads on cluster nodes while balancing
CPU and memory, avoiding capacity violations, reducing cross-zone traffic,
and spreading replicas. The model is intentionally small enough to inspect.
"""

import argparse
from dataclasses import dataclass
from math import exp
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

type Placement = tuple[int, ...]


@dataclass(frozen=True)
class Node:
    """A schedulable node with CPU and memory capacity."""

    name: str
    zone: str
    cpu: float
    memory: float


@dataclass(frozen=True)
class Workload:
    """One workload instance and its requested resources."""

    name: str
    cpu: float
    memory: float
    spread_group: str | None = None


@dataclass(frozen=True)
class Traffic:
    """Relative traffic rate between two workload instances."""

    source: str
    target: str
    rate: float


@dataclass(frozen=True)
class ScoreWeights:
    """Weights that turn placement trade-offs into one scalar energy."""

    capacity: float = 10_000.0
    balance: float = 40.0
    network: float = 1.0
    spread_node: float = 120.0
    spread_zone: float = 12.0


@dataclass(frozen=True)
class Score:
    """Weighted components of the placement objective."""

    capacity: float
    balance: float
    network: float
    spread: float

    @property
    def total(self) -> float:
        """Return total energy; lower is better."""
        return self.capacity + self.balance + self.network + self.spread


@dataclass(frozen=True)
class AnnealingConfig:
    """Cooling schedule and stopping condition."""

    initial_temperature: float = 80.0
    cooling_rate: float = 0.998
    steps: int = 5_000


@dataclass(frozen=True)
class TracePoint:
    """One observed state of the annealing process."""

    step: int
    temperature: float
    current_energy: float
    best_energy: float
    accepted: bool


@dataclass(frozen=True)
class AnnealingResult:
    """Initial, final, and best placements plus convergence history."""

    initial: Placement
    final: Placement
    best: Placement
    trace: tuple[TracePoint, ...]


class Arguments(argparse.Namespace):
    """Typed command-line arguments populated by argparse."""

    def __init__(self) -> None:
        super().__init__()
        self.html: Path | None = None
        self.show = False


NODES: tuple[Node, ...] = (
    Node("node-a1", "zone-a", cpu=8, memory=16),
    Node("node-a2", "zone-a", cpu=8, memory=16),
    Node("node-b1", "zone-b", cpu=8, memory=16),
    Node("node-b2", "zone-b", cpu=8, memory=16),
)

WORKLOADS: tuple[Workload, ...] = (
    Workload("frontend-1", cpu=2, memory=2, spread_group="frontend"),
    Workload("frontend-2", cpu=2, memory=2, spread_group="frontend"),
    Workload("api-1", cpu=3, memory=4, spread_group="api"),
    Workload("api-2", cpu=3, memory=4, spread_group="api"),
    Workload("worker", cpu=4, memory=6),
    Workload("postgres", cpu=4, memory=8),
    Workload("redis", cpu=2, memory=4),
    Workload("metrics", cpu=1, memory=2),
)

TRAFFIC: tuple[Traffic, ...] = (
    Traffic("frontend-1", "api-1", 8),
    Traffic("frontend-2", "api-2", 8),
    Traffic("api-1", "postgres", 6),
    Traffic("api-2", "postgres", 6),
    Traffic("api-1", "redis", 5),
    Traffic("api-2", "redis", 5),
    Traffic("worker", "postgres", 4),
    Traffic("worker", "redis", 3),
    Traffic("metrics", "frontend-1", 1),
    Traffic("metrics", "frontend-2", 1),
)

WEIGHTS = ScoreWeights()
CONFIG = AnnealingConfig()


# %%
# @title Objective function


def resource_usage(
    placement: Placement,
    nodes: tuple[Node, ...],
    workloads: tuple[Workload, ...],
) -> tuple[tuple[float, float], ...]:
    """Return `(cpu, memory)` usage for every node."""
    if len(placement) != len(workloads):
        raise ValueError("placement must assign every workload")

    usage = [[0.0, 0.0] for _ in nodes]
    for node_index, workload in zip(placement, workloads, strict=True):
        if not 0 <= node_index < len(nodes):
            raise ValueError(f"invalid node index: {node_index}")
        usage[node_index][0] += workload.cpu
        usage[node_index][1] += workload.memory
    return tuple((cpu, memory) for cpu, memory in usage)


def network_distance(left: Node, right: Node) -> int:
    """Return 0 for one node, 1 within a zone, and 4 across zones."""
    if left.name == right.name:
        return 0
    if left.zone == right.zone:
        return 1
    return 4


def score_placement(
    placement: Placement,
    nodes: tuple[Node, ...] = NODES,
    workloads: tuple[Workload, ...] = WORKLOADS,
    traffic: tuple[Traffic, ...] = TRAFFIC,
    weights: ScoreWeights = WEIGHTS,
) -> Score:
    """Calculate capacity, balance, network, and replica-spread costs."""
    usage = resource_usage(placement, nodes, workloads)

    capacity = 0.0
    for node, (used_cpu, used_memory) in zip(nodes, usage, strict=True):
        cpu_over = max(0.0, used_cpu / node.cpu - 1.0)
        memory_over = max(0.0, used_memory / node.memory - 1.0)
        capacity += weights.capacity * (cpu_over**2 + memory_over**2)

    target_cpu = sum(w.cpu for w in workloads) / sum(n.cpu for n in nodes)
    target_memory = sum(w.memory for w in workloads) / sum(
        n.memory for n in nodes
    )
    balance = weights.balance * sum(
        (used_cpu / node.cpu - target_cpu) ** 2
        + (used_memory / node.memory - target_memory) ** 2
        for node, (used_cpu, used_memory) in zip(nodes, usage, strict=True)
    )

    workload_index = {workload.name: i for i, workload in enumerate(workloads)}
    network = (
        sum(
            edge.rate
            * network_distance(
                nodes[placement[workload_index[edge.source]]],
                nodes[placement[workload_index[edge.target]]],
            )
            for edge in traffic
        )
        * weights.network
    )

    spread = 0.0
    for left_index, left in enumerate(workloads):
        if left.spread_group is None:
            continue
        for right_index in range(left_index + 1, len(workloads)):
            right = workloads[right_index]
            if left.spread_group != right.spread_group:
                continue
            left_node = nodes[placement[left_index]]
            right_node = nodes[placement[right_index]]
            if left_node.name == right_node.name:
                spread += weights.spread_node
            elif left_node.zone == right_node.zone:
                spread += weights.spread_zone

    return Score(capacity, balance, network, spread)


def is_feasible(
    placement: Placement,
    nodes: tuple[Node, ...] = NODES,
    workloads: tuple[Workload, ...] = WORKLOADS,
) -> bool:
    """Return whether no node exceeds CPU or memory capacity."""
    return all(
        used_cpu <= node.cpu and used_memory <= node.memory
        for node, (used_cpu, used_memory) in zip(
            nodes,
            resource_usage(placement, nodes, workloads),
            strict=True,
        )
    )


# %%
# @title Baselines and neighborhood


def random_feasible_placement(
    rng: np.random.Generator,
    nodes: tuple[Node, ...] = NODES,
    workloads: tuple[Workload, ...] = WORKLOADS,
    max_attempts: int = 10_000,
) -> Placement:
    """Sample complete placements until one satisfies node capacity."""
    for _ in range(max_attempts):
        placement = tuple(
            int(value) for value in rng.integers(0, len(nodes), len(workloads))
        )
        if is_feasible(placement, nodes, workloads):
            return placement
    raise RuntimeError("could not sample a feasible placement")


def greedy_placement(
    nodes: tuple[Node, ...] = NODES,
    workloads: tuple[Workload, ...] = WORKLOADS,
) -> Placement:
    """Place largest workloads first on the least-loaded feasible node."""
    placement = [-1] * len(workloads)
    usage = [[0.0, 0.0] for _ in nodes]
    order = sorted(
        range(len(workloads)),
        key=lambda i: workloads[i].cpu + workloads[i].memory,
        reverse=True,
    )

    for workload_index in order:
        workload = workloads[workload_index]
        feasible = [
            i
            for i, node in enumerate(nodes)
            if usage[i][0] + workload.cpu <= node.cpu
            and usage[i][1] + workload.memory <= node.memory
        ]
        if not feasible:
            raise RuntimeError(f"greedy placement failed at {workload.name}")

        node_index = min(
            feasible,
            key=lambda i: max(
                (usage[i][0] + workload.cpu) / nodes[i].cpu,
                (usage[i][1] + workload.memory) / nodes[i].memory,
            ),
        )
        placement[workload_index] = node_index
        usage[node_index][0] += workload.cpu
        usage[node_index][1] += workload.memory

    return tuple(placement)


def random_neighbor(
    placement: Placement,
    node_count: int,
    rng: np.random.Generator,
) -> Placement:
    """Move one randomly chosen workload to a different node."""
    workload_index = int(rng.integers(0, len(placement)))
    old_node = placement[workload_index]
    new_node = int(rng.integers(0, node_count - 1))
    if new_node >= old_node:
        new_node += 1
    return (
        placement[:workload_index]
        + (new_node,)
        + placement[workload_index + 1 :]
    )


def acceptance_probability(delta_energy: float, temperature: float) -> float:
    """Return the Metropolis probability of accepting a candidate move."""
    if delta_energy <= 0:
        return 1.0
    return exp(-delta_energy / max(temperature, 1e-12))


# %%
# @title Anneal


def anneal(
    initial: Placement,
    rng: np.random.Generator,
    config: AnnealingConfig = CONFIG,
    nodes: tuple[Node, ...] = NODES,
    workloads: tuple[Workload, ...] = WORKLOADS,
    traffic: tuple[Traffic, ...] = TRAFFIC,
    weights: ScoreWeights = WEIGHTS,
) -> AnnealingResult:
    """Explore placement space with geometric cooling."""
    if config.initial_temperature <= 0:
        raise ValueError("initial temperature must be positive")
    if not 0 < config.cooling_rate < 1:
        raise ValueError("cooling rate must be between 0 and 1")
    if config.steps <= 0:
        raise ValueError("steps must be positive")

    current = initial
    current_energy = score_placement(
        current, nodes, workloads, traffic, weights
    ).total
    best = current
    best_energy = current_energy
    trace = [
        TracePoint(
            0, config.initial_temperature, current_energy, best_energy, True
        )
    ]

    for step in range(1, config.steps + 1):
        temperature = config.initial_temperature * config.cooling_rate**step
        candidate = random_neighbor(current, len(nodes), rng)
        candidate_energy = score_placement(
            candidate, nodes, workloads, traffic, weights
        ).total
        delta = candidate_energy - current_energy
        accepted = rng.random() < acceptance_probability(delta, temperature)

        if accepted:
            current = candidate
            current_energy = candidate_energy
            if current_energy < best_energy:
                best = current
                best_energy = current_energy

        trace.append(
            TracePoint(
                step, temperature, current_energy, best_energy, accepted
            )
        )

    return AnnealingResult(initial, current, best, tuple(trace))


# %%
# @title Report and plot


def placement_by_node(
    placement: Placement,
    nodes: tuple[Node, ...] = NODES,
    workloads: tuple[Workload, ...] = WORKLOADS,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Group workload names by assigned node."""
    grouped = tuple(
        tuple(
            workload.name
            for node_index, workload in zip(placement, workloads, strict=True)
            if node_index == i
        )
        for i in range(len(nodes))
    )
    return tuple(
        (node.name, names) for node, names in zip(nodes, grouped, strict=True)
    )


def print_report(
    initial: Placement,
    greedy: Placement,
    result: AnnealingResult,
) -> None:
    """Print baseline scores and the best annealed placement."""
    candidates = (
        ("random", initial),
        ("greedy", greedy),
        ("annealed", result.best),
    )
    print("placement score (lower is better)\n")
    print(
        f"{'method':<10} {'total':>8} {'capacity':>10} {'balance':>9} {'network':>9} {'spread':>8}"
    )
    print("-" * 60)
    for label, placement in candidates:
        score = score_placement(placement)
        print(
            f"{label:<10} {score.total:>8.2f} {score.capacity:>10.2f} "
            f"{score.balance:>9.2f} {score.network:>9.2f} {score.spread:>8.2f}"
        )

    accepted = sum(point.accepted for point in result.trace[1:])
    print(f"\naccepted moves: {accepted}/{len(result.trace) - 1}")
    print("\nbest placement:")
    for node_name, workloads in placement_by_node(result.best):
        print(f"  {node_name:<8}  {', '.join(workloads) or '-'}")


def build_figure(
    initial: Placement,
    greedy: Placement,
    result: AnnealingResult,
) -> go.Figure:
    """Build convergence, temperature, score, and utilization plots."""
    figure = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Energy convergence",
            "Cooling schedule",
            "Objective breakdown",
            "Annealed node utilization",
        ),
        vertical_spacing=0.16,
    )

    steps = [point.step for point in result.trace]
    figure.add_trace(
        go.Scatter(
            x=steps,
            y=[point.current_energy for point in result.trace],
            name="current energy",
            line={"color": "#5e81ac", "width": 1},
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=steps,
            y=[point.best_energy for point in result.trace],
            name="best energy",
            line={"color": "#a3be8c", "width": 3},
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=steps,
            y=[point.temperature for point in result.trace],
            name="temperature",
            line={"color": "#d08770"},
        ),
        row=1,
        col=2,
    )

    labels = ("random", "greedy", "annealed")
    scores = tuple(score_placement(p) for p in (initial, greedy, result.best))
    for component, color in (
        ("capacity", "#bf616a"),
        ("balance", "#ebcb8b"),
        ("network", "#88c0d0"),
        ("spread", "#b48ead"),
    ):
        figure.add_trace(
            go.Bar(
                x=labels,
                y=[getattr(score, component) for score in scores],
                name=component,
                marker_color=color,
            ),
            row=2,
            col=1,
        )

    usage = resource_usage(result.best, NODES, WORKLOADS)
    node_names = [node.name for node in NODES]
    figure.add_trace(
        go.Bar(
            x=node_names,
            y=[
                used_cpu / node.cpu * 100
                for node, (used_cpu, _) in zip(NODES, usage, strict=True)
            ],
            name="CPU %",
            marker_color="#5e81ac",
        ),
        row=2,
        col=2,
    )
    figure.add_trace(
        go.Bar(
            x=node_names,
            y=[
                used_memory / node.memory * 100
                for node, (_, used_memory) in zip(NODES, usage, strict=True)
            ],
            name="memory %",
            marker_color="#a3be8c",
        ),
        row=2,
        col=2,
    )

    figure.update_yaxes(title_text="energy", row=1, col=1)
    figure.update_yaxes(title_text="temperature", type="log", row=1, col=2)
    figure.update_yaxes(title_text="weighted cost", row=2, col=1)
    figure.update_yaxes(
        title_text="utilization %", range=[0, 110], row=2, col=2
    )
    figure.update_layout(
        title="Simulated annealing - workload placement",
        barmode="group",
        height=760,
        legend={"orientation": "h", "y": -0.16},
        margin={"b": 120},
    )
    return figure


def parse_args() -> Arguments:
    """Parse command-line output options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--html",
        type=Path,
        help="write the interactive Plotly figure to this file",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="open the Plotly figure in a browser",
    )
    return parser.parse_args(namespace=Arguments())


def main() -> None:
    """Run the deterministic lab and render requested outputs."""
    args = parse_args()
    rng = np.random.default_rng(seed=42)
    initial = random_feasible_placement(rng)
    greedy = greedy_placement()
    result = anneal(initial, rng)
    print_report(initial, greedy, result)

    if args.html or args.show:
        figure = build_figure(initial, greedy, result)
        if args.html:
            figure.write_html(args.html)
            print(f"\nwrote {args.html}")
        if args.show:
            figure.show()


if __name__ == "__main__":
    main()
