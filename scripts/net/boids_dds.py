#!/usr/bin/env python3
# mypy: disable-error-code=import-not-found
"""Boids lab with deterministic local and distributed DDS modes."""

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import plotly.graph_objects as go


@dataclass(frozen=True)
class Boid:
    """One simulated agent owned by one process."""

    boid_id: int
    owner_id: int
    position: np.ndarray
    velocity: np.ndarray


@dataclass(frozen=True)
class BoidsConfig:
    """World geometry and steering limits."""

    width: float = 100.0
    height: float = 70.0
    perception_radius: float = 14.0
    separation_radius: float = 5.0
    separation_weight: float = 1.8
    alignment_weight: float = 1.0
    cohesion_weight: float = 0.8
    max_speed: float = 8.0
    max_acceleration: float = 5.0
    time_step: float = 0.05

    @property
    def world_size(self) -> np.ndarray:
        """Return world width and height as a vector."""
        return np.array([self.width, self.height], dtype=np.float64)


@dataclass(frozen=True)
class CachedBoid:
    """Latest remote state and its local arrival time."""

    boid: Boid
    tick: int
    received_at: float
    publication_handle: int | None


type Snapshot = tuple[Boid, ...]
type RecordedFrame = tuple[float, Snapshot]


def limit(vector: np.ndarray, maximum: float) -> np.ndarray:
    """Return VECTOR with magnitude capped at MAXIMUM."""
    magnitude = float(np.linalg.norm(vector))
    if magnitude <= maximum or magnitude == 0.0:
        return vector
    return vector * (maximum / magnitude)


def wrapped_delta(
    origin: np.ndarray,
    target: np.ndarray,
    world_size: np.ndarray,
) -> np.ndarray:
    """Return the shortest displacement on a toroidal world."""
    return (target - origin + world_size / 2.0) % world_size - world_size / 2.0


def wrap_position(position: np.ndarray, world_size: np.ndarray) -> np.ndarray:
    """Wrap POSITION while keeping floating-point results below WORLD_SIZE."""
    wrapped = position % world_size
    upper_bound = np.nextafter(world_size, np.zeros_like(world_size))
    return np.minimum(wrapped, upper_bound)


def steer_toward(
    direction: np.ndarray,
    velocity: np.ndarray,
    maximum_speed: float,
    maximum_acceleration: float,
) -> np.ndarray:
    """Steer from current velocity toward DIRECTION."""
    magnitude = float(np.linalg.norm(direction))
    if magnitude == 0.0:
        return np.zeros(2, dtype=np.float64)
    desired = direction * (maximum_speed / magnitude)
    return limit(desired - velocity, maximum_acceleration)


def initialize_boids(
    count: int,
    owner_id: int,
    seed: int,
    config: BoidsConfig,
) -> Snapshot:
    """Create a deterministic group with globally unique IDs."""
    if count <= 0:
        raise ValueError("count must be positive")
    if not 0 <= owner_id < 2_000:
        raise ValueError("owner_id must be in the range 0..1999")
    if count >= 1_000_000:
        raise ValueError("count must be smaller than 1,000,000")

    rng = np.random.default_rng(seed)
    positions = rng.uniform([0.0, 0.0], config.world_size, size=(count, 2))
    angles = rng.uniform(0.0, 2.0 * np.pi, size=count)
    speeds = rng.uniform(
        config.max_speed * 0.35,
        config.max_speed * 0.75,
        size=count,
    )
    velocities = np.column_stack((np.cos(angles), np.sin(angles)))
    velocities *= speeds[:, np.newaxis]
    id_base = owner_id * 1_000_000
    return tuple(
        Boid(
            boid_id=id_base + index,
            owner_id=owner_id,
            position=positions[index],
            velocity=velocities[index],
        )
        for index in range(count)
    )


def step_boids(
    local_boids: Snapshot,
    visible_boids: Snapshot,
    config: BoidsConfig,
) -> Snapshot:
    """Advance owned boids synchronously from one shared snapshot."""
    world_size = config.world_size
    updated: list[Boid] = []

    for boid in local_boids:
        neighbours: list[Boid] = []
        displacements: list[np.ndarray] = []
        distances: list[float] = []

        for candidate in visible_boids:
            if candidate.boid_id == boid.boid_id:
                continue
            displacement = wrapped_delta(
                boid.position,
                candidate.position,
                world_size,
            )
            distance = float(np.linalg.norm(displacement))
            if 0.0 < distance <= config.perception_radius:
                neighbours.append(candidate)
                displacements.append(displacement)
                distances.append(distance)

        acceleration = np.zeros(2, dtype=np.float64)
        if neighbours:
            alignment_direction = np.mean(
                [candidate.velocity for candidate in neighbours],
                axis=0,
            )
            cohesion_direction = np.mean(displacements, axis=0)

            close_displacements = [
                displacement / max(distance * distance, 1e-12)
                for displacement, distance in zip(
                    displacements,
                    distances,
                    strict=True,
                )
                if distance <= config.separation_radius
            ]
            separation_direction = (
                -np.sum(close_displacements, axis=0)
                if close_displacements
                else np.zeros(2, dtype=np.float64)
            )

            separation = steer_toward(
                separation_direction,
                boid.velocity,
                config.max_speed,
                config.max_acceleration,
            )
            alignment = steer_toward(
                alignment_direction,
                boid.velocity,
                config.max_speed,
                config.max_acceleration,
            )
            cohesion = steer_toward(
                cohesion_direction,
                boid.velocity,
                config.max_speed,
                config.max_acceleration,
            )
            acceleration = (
                config.separation_weight * separation
                + config.alignment_weight * alignment
                + config.cohesion_weight * cohesion
            )
            acceleration = limit(acceleration, config.max_acceleration)

        velocity = limit(
            boid.velocity + acceleration * config.time_step,
            config.max_speed,
        )
        position = wrap_position(
            boid.position + velocity * config.time_step,
            world_size,
        )
        updated.append(
            Boid(
                boid_id=boid.boid_id,
                owner_id=boid.owner_id,
                position=position,
                velocity=velocity,
            )
        )

    return tuple(updated)


def flock_metrics(boids: Snapshot, config: BoidsConfig) -> dict[str, float]:
    """Calculate polarization, neighbour density, and mean speed."""
    if not boids:
        return {"polarization": 0.0, "mean_neighbours": 0.0, "mean_speed": 0.0}

    velocities = np.array([boid.velocity for boid in boids])
    speeds = np.linalg.norm(velocities, axis=1)
    unit_velocities = velocities / np.maximum(speeds[:, np.newaxis], 1e-12)
    polarization = float(np.linalg.norm(np.mean(unit_velocities, axis=0)))

    neighbour_counts: list[int] = []
    for boid in boids:
        count = 0
        for candidate in boids:
            if candidate.boid_id == boid.boid_id:
                continue
            distance = np.linalg.norm(
                wrapped_delta(
                    boid.position,
                    candidate.position,
                    config.world_size,
                )
            )
            count += int(distance <= config.perception_radius)
        neighbour_counts.append(count)

    return {
        "polarization": polarization,
        "mean_neighbours": float(np.mean(neighbour_counts)),
        "mean_speed": float(np.mean(speeds)),
    }


def print_summary(
    mode: str,
    counter: int,
    boids: Snapshot,
    config: BoidsConfig,
    counter_name: str = "tick",
) -> None:
    """Print one machine-readable simulation summary."""
    owners = {boid.owner_id for boid in boids}
    summary: dict[str, float | int | str] = {
        "mode": mode,
        "boids": len(boids),
        "owners": len(owners),
        **flock_metrics(boids, config),
    }
    summary[counter_name] = counter
    print(json.dumps(summary, sort_keys=True))


def owner_palette(owners: list[int]) -> dict[int, str]:
    """Assign stable contrasting colors to process owners."""
    colors = [
        "#0072B2",
        "#D55E00",
        "#009E73",
        "#CC79A7",
        "#E69F00",
        "#56B4E9",
        "#6F42C1",
        "#333333",
    ]
    return {
        owner: colors[index % len(colors)]
        for index, owner in enumerate(owners)
    }


def write_animation(
    frames: list[RecordedFrame],
    destination: Path,
    config: BoidsConfig,
    title: str,
) -> None:
    """Write a self-contained animated Plotly report."""
    if not frames:
        raise ValueError("cannot render an empty recording")

    owners = sorted({boid.owner_id for _, frame in frames for boid in frame})
    colors = owner_palette(owners)

    def traces(snapshot: Snapshot) -> list[go.Scatter]:
        result: list[go.Scatter] = []
        for owner in owners:
            group = [boid for boid in snapshot if boid.owner_id == owner]
            result.append(
                go.Scatter(
                    x=[boid.position[0] for boid in group],
                    y=[boid.position[1] for boid in group],
                    mode="markers",
                    name=f"owner {owner}",
                    marker={"color": colors[owner], "size": 9},
                    customdata=[boid.boid_id for boid in group],
                    hovertemplate=(
                        "boid=%{customdata}<br>x=%{x:.2f}<br>y=%{y:.2f}"
                        "<extra></extra>"
                    ),
                )
            )
        return result

    plotly_frames = [
        go.Frame(
            data=traces(snapshot),
            name=str(index),
            layout=go.Layout(title_text=f"{title} | t={elapsed:.2f}s"),
        )
        for index, (elapsed, snapshot) in enumerate(frames)
    ]
    steps = [
        {
            "args": [
                [frame.name],
                {
                    "frame": {"duration": 0, "redraw": True},
                    "mode": "immediate",
                },
            ],
            "label": f"{frames[index][0]:.1f}",
            "method": "animate",
        }
        for index, frame in enumerate(plotly_frames)
    ]
    figure = go.Figure(data=traces(frames[0][1]), frames=plotly_frames)
    figure.update_layout(
        title=f"{title} | t={frames[0][0]:.2f}s",
        template="plotly_white",
        xaxis={"range": [0, config.width], "title": "x"},
        yaxis={
            "range": [0, config.height],
            "title": "y",
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        width=1000,
        height=720,
        sliders=[
            {"active": 0, "currentvalue": {"prefix": "t = "}, "steps": steps}
        ],
        updatemenus=[
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 60, "redraw": True},
                                "fromcurrent": True,
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                            },
                        ],
                    },
                ],
            }
        ],
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(destination, include_plotlyjs=True)


def load_dds() -> SimpleNamespace:
    """Import optional Cyclone DDS bindings and define the wire type."""
    try:
        from cyclonedds.core import (
            Policy,
            Qos,
        )
        from cyclonedds.domain import (
            DomainParticipant,
        )
        from cyclonedds.idl import IdlStruct
        from cyclonedds.idl.annotations import key
        from cyclonedds.idl.types import (
            float64,
            int32,
            uint64,
        )
        from cyclonedds.pub import DataWriter
        from cyclonedds.sub import DataReader
        from cyclonedds.topic import Topic
        from cyclonedds.util import duration
    except ImportError as error:
        raise SystemExit(
            "DDS mode requires uv run --with 'cyclonedds>=11.0.1,<12'"
        ) from error

    @dataclass
    class BoidSample(  # type: ignore[call-arg]
        IdlStruct,
        typename="Deck.BoidState",
    ):
        """Keyed DDS sample shared by every lab participant."""

        boid_id: int32
        key("boid_id")
        owner_id: int32
        tick: uint64
        x: float64
        y: float64
        vx: float64
        vy: float64

    return SimpleNamespace(
        BoidSample=BoidSample,
        DataReader=DataReader,
        DataWriter=DataWriter,
        DomainParticipant=DomainParticipant,
        Policy=Policy,
        Qos=Qos,
        Topic=Topic,
        duration=duration,
    )


def dds_qos(dds: SimpleNamespace, reliable: bool) -> Any:
    """Return latest-state QoS shared by readers and writers."""
    reliability = (
        dds.Policy.Reliability.Reliable(
            max_blocking_time=dds.duration(milliseconds=50)
        )
        if reliable
        else dds.Policy.Reliability.BestEffort
    )
    return dds.Qos(
        reliability,
        dds.Policy.Durability.Volatile,
        dds.Policy.History.KeepLast(1),
    )


def boid_to_sample(dds: SimpleNamespace, boid: Boid, tick: int) -> Any:
    """Convert an in-memory boid to its DDS representation."""
    return dds.BoidSample(
        boid_id=boid.boid_id,
        owner_id=boid.owner_id,
        tick=tick,
        x=float(boid.position[0]),
        y=float(boid.position[1]),
        vx=float(boid.velocity[0]),
        vy=float(boid.velocity[1]),
    )


def sample_to_boid(sample: Any) -> Boid:
    """Convert a DDS sample to an in-memory boid."""
    return Boid(
        boid_id=int(sample.boid_id),
        owner_id=int(sample.owner_id),
        position=np.array([sample.x, sample.y], dtype=np.float64),
        velocity=np.array([sample.vx, sample.vy], dtype=np.float64),
    )


def drain_reader(
    reader: Any,
    cache: dict[int, CachedBoid],
    own_owner_id: int | None,
) -> None:
    """Take available samples, retaining the newest tick per instance."""
    received_at = time.monotonic()
    for sample in reader.take(N=100_000):
        sample_info = getattr(sample, "sample_info", None)
        if sample_info is not None and not sample_info.valid_data:
            key_sample = getattr(sample, "key_sample", None)
            if key_sample is not None and hasattr(key_sample, "boid_id"):
                boid_id = int(key_sample.boid_id)
                cached = cache.get(boid_id)
                lifecycle_handle = int(sample_info.publication_handle)
                if cached is not None and (
                    cached.publication_handle is None
                    or cached.publication_handle == lifecycle_handle
                ):
                    cache.pop(boid_id)
            continue
        if own_owner_id is not None and int(sample.owner_id) == own_owner_id:
            continue
        publication_handle = (
            int(sample_info.publication_handle)
            if sample_info is not None
            else None
        )
        cached = cache.get(int(sample.boid_id))
        if (
            cached is not None
            and cached.publication_handle == publication_handle
            and int(sample.tick) < cached.tick
        ):
            continue
        cache[int(sample.boid_id)] = CachedBoid(
            boid=sample_to_boid(sample),
            tick=int(sample.tick),
            received_at=received_at,
            publication_handle=publication_handle,
        )


def prune_cache(cache: dict[int, CachedBoid], stale_after: float) -> None:
    """Remove remote state not refreshed within STALE_AFTER seconds."""
    cutoff = time.monotonic() - stale_after
    stale_ids = [
        boid_id
        for boid_id, cached in cache.items()
        if cached.received_at < cutoff
    ]
    for boid_id in stale_ids:
        del cache[boid_id]


def run_local(args: argparse.Namespace, config: BoidsConfig) -> None:
    """Run a deterministic single-process flock."""
    boids = initialize_boids(args.agents, 0, args.seed, config)
    frames: list[RecordedFrame] = [(0.0, boids)]
    for tick in range(1, args.steps + 1):
        boids = step_boids(boids, boids, config)
        if tick % args.record_every == 0:
            frames.append((tick * config.time_step, boids))

    print_summary("local", args.steps, boids, config)
    if args.html is not None:
        write_animation(frames, args.html, config, "Local Boids")
        print(f"wrote {args.html}")


def run_node(args: argparse.Namespace, config: BoidsConfig) -> None:
    """Own one shard of boids and exchange state through DDS."""
    dds = load_dds()
    participant = dds.DomainParticipant(args.domain)
    topic = dds.Topic(participant, args.topic, dds.BoidSample)
    qos = dds_qos(dds, args.reliable)
    writer = dds.DataWriter(participant, topic, qos=qos)
    reader = dds.DataReader(participant, topic, qos=qos)

    local = initialize_boids(
        args.agents,
        args.node_id,
        args.seed + args.node_id,
        config,
    )
    remote: dict[int, CachedBoid] = {}
    frames: list[RecordedFrame] = [(0.0, local)]

    time.sleep(args.discovery_wait)
    period = 1.0 / args.hz
    started_at = time.monotonic()
    next_tick_at = started_at
    report_ticks = max(1, round(args.report_every * args.hz))

    for tick in range(args.steps + 1):
        drain_reader(reader, remote, args.node_id)
        prune_cache(remote, args.stale_after)
        visible = local + tuple(cached.boid for cached in remote.values())

        if tick > 0:
            local = step_boids(local, visible, config)
        for boid in local:
            writer.write(boid_to_sample(dds, boid, tick))

        if tick % args.record_every == 0:
            combined = local + tuple(cached.boid for cached in remote.values())
            frames.append((time.monotonic() - started_at, combined))
        if tick % report_ticks == 0:
            combined = local + tuple(cached.boid for cached in remote.values())
            print_summary(f"node-{args.node_id}", tick, combined, config)

        next_tick_at += period
        time.sleep(max(0.0, next_tick_at - time.monotonic()))

    if args.html is not None:
        write_animation(frames, args.html, config, f"DDS Node {args.node_id}")
        print(f"wrote {args.html}")


def run_observer(args: argparse.Namespace, config: BoidsConfig) -> None:
    """Observe DDS state without publishing or steering boids."""
    dds = load_dds()
    participant = dds.DomainParticipant(args.domain)
    topic = dds.Topic(participant, args.topic, dds.BoidSample)
    reader = dds.DataReader(
        participant,
        topic,
        qos=dds_qos(dds, args.reliable),
    )
    cache: dict[int, CachedBoid] = {}
    frames: list[RecordedFrame] = []
    period = 1.0 / args.hz
    started_at = time.monotonic()
    deadline = started_at + args.seconds
    next_poll_at = started_at

    while time.monotonic() < deadline:
        drain_reader(reader, cache, None)
        prune_cache(cache, args.stale_after)
        snapshot = tuple(cached.boid for cached in cache.values())
        frames.append((time.monotonic() - started_at, snapshot))
        next_poll_at += period
        time.sleep(max(0.0, next_poll_at - time.monotonic()))

    snapshot = tuple(cached.boid for cached in cache.values())
    peak_snapshot = max(
        (recorded_snapshot for _, recorded_snapshot in frames),
        key=len,
        default=(),
    )
    print_summary(
        "observer-peak",
        len(frames),
        peak_snapshot,
        config,
        counter_name="poll",
    )
    print_summary(
        "observer-final",
        len(frames),
        snapshot,
        config,
        counter_name="poll",
    )
    non_empty_frames = [frame for frame in frames if frame[1]]
    if args.html is not None and non_empty_frames:
        write_animation(non_empty_frames, args.html, config, "DDS Observer")
        print(f"wrote {args.html}")
    elif args.html is not None:
        raise SystemExit("observer received no samples; no HTML written")


def run_self_test() -> None:
    """Exercise deterministic invariants without requiring DDS."""
    config = BoidsConfig()
    left = np.array([1.0, 2.0])
    right = np.array([99.0, 68.0])
    np.testing.assert_allclose(
        wrapped_delta(left, right, config.world_size),
        np.array([-2.0, -4.0]),
    )

    initial = initialize_boids(24, 3, 42, config)
    first = initial
    second = initialize_boids(24, 3, 42, config)
    for _ in range(100):
        first = step_boids(first, first, config)
        second = step_boids(second, second, config)

    for left_boid, right_boid in zip(first, second, strict=True):
        np.testing.assert_allclose(left_boid.position, right_boid.position)
        np.testing.assert_allclose(left_boid.velocity, right_boid.velocity)
        assert np.all(left_boid.position >= 0.0)
        assert np.all(left_boid.position < config.world_size)
        assert np.linalg.norm(left_boid.velocity) <= config.max_speed + 1e-12

    np.testing.assert_allclose(
        first[0].position,
        np.array([55.988300302507334, 23.245877482749407]),
        rtol=0.0,
        atol=1e-9,
    )
    np.testing.assert_allclose(
        first[0].velocity,
        np.array([-6.100084133612904, 0.4441625927753482]),
        rtol=0.0,
        atol=1e-9,
    )

    class FakeReader:
        """Return one fixed batch through the subset of DataReader we use."""

        def __init__(self, samples: list[SimpleNamespace]) -> None:
            self.samples = samples

        def take(self, N: int) -> list[SimpleNamespace]:
            assert N > 0
            return self.samples

    def fake_sample(
        boid: Boid,
        tick: int,
        publication_handle: int,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            boid_id=boid.boid_id,
            owner_id=boid.owner_id,
            tick=tick,
            x=float(boid.position[0]),
            y=float(boid.position[1]),
            vx=float(boid.velocity[0]),
            vy=float(boid.velocity[1]),
            sample_info=SimpleNamespace(
                valid_data=True,
                publication_handle=publication_handle,
            ),
        )

    now = time.monotonic()
    cache = {
        initial[0].boid_id: CachedBoid(
            boid=initial[0],
            tick=10,
            received_at=now,
            publication_handle=101,
        )
    }
    drain_reader(FakeReader([fake_sample(initial[0], 9, 101)]), cache, None)
    assert cache[initial[0].boid_id].tick == 10

    drain_reader(FakeReader([fake_sample(initial[0], 0, 202)]), cache, None)
    assert cache[initial[0].boid_id].tick == 0
    assert cache[initial[0].boid_id].publication_handle == 202

    def invalid_sample(publication_handle: int) -> SimpleNamespace:
        return SimpleNamespace(
            key_sample=SimpleNamespace(boid_id=initial[0].boid_id),
            sample_info=SimpleNamespace(
                valid_data=False,
                publication_handle=publication_handle,
            ),
        )

    drain_reader(FakeReader([invalid_sample(101)]), cache, None)
    assert initial[0].boid_id in cache
    drain_reader(FakeReader([invalid_sample(202)]), cache, None)
    assert initial[0].boid_id not in cache

    cache = {
        initial[0].boid_id: CachedBoid(initial[0], 0, now - 2.0, 101),
        initial[1].boid_id: CachedBoid(initial[1], 0, now, 101),
    }
    prune_cache(cache, stale_after=1.0)
    assert set(cache) == {initial[1].boid_id}

    loopback_cache: dict[int, CachedBoid] = {}
    drain_reader(
        FakeReader([fake_sample(initial[0], 0, 101)]),
        loopback_cache,
        own_owner_id=initial[0].owner_id,
    )
    assert not loopback_cache
    print("self-test: ok")


def add_world_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared world and steering arguments to PARSER."""
    parser.add_argument("--width", type=float, default=100.0)
    parser.add_argument("--height", type=float, default=70.0)
    parser.add_argument("--perception", type=float, default=14.0)
    parser.add_argument("--separation-radius", type=float, default=5.0)
    parser.add_argument("--separation-weight", type=float, default=1.8)
    parser.add_argument("--alignment-weight", type=float, default=1.0)
    parser.add_argument("--cohesion-weight", type=float, default=0.8)
    parser.add_argument("--max-speed", type=float, default=8.0)
    parser.add_argument("--max-acceleration", type=float, default=5.0)
    parser.add_argument("--time-step", type=float, default=0.05)


def add_dds_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared DDS arguments to PARSER."""
    parser.add_argument("--domain", type=int, default=42)
    parser.add_argument("--topic", default="Deck.BoidState")
    parser.add_argument("--reliable", action="store_true")
    parser.add_argument("--stale-after", type=float, default=1.0)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    local = subparsers.add_parser("local", help="run without DDS")
    add_world_arguments(local)
    local.add_argument("--agents", type=int, default=60)
    local.add_argument("--steps", type=int, default=500)
    local.add_argument("--seed", type=int, default=42)
    local.add_argument("--record-every", type=int, default=5)
    local.add_argument("--html", type=Path)

    node = subparsers.add_parser("node", help="run one DDS flock shard")
    add_world_arguments(node)
    add_dds_arguments(node)
    node.add_argument("--node-id", type=int, required=True)
    node.add_argument("--agents", type=int, default=20)
    node.add_argument("--steps", type=int, default=200)
    node.add_argument("--hz", type=float, default=20.0)
    node.add_argument("--seed", type=int, default=42)
    node.add_argument("--discovery-wait", type=float, default=1.0)
    node.add_argument("--report-every", type=float, default=2.0)
    node.add_argument("--record-every", type=int, default=2)
    node.add_argument("--html", type=Path)

    observer = subparsers.add_parser(
        "observe",
        help="record DDS state without publishing",
    )
    add_world_arguments(observer)
    add_dds_arguments(observer)
    observer.add_argument("--seconds", type=float, default=12.0)
    observer.add_argument("--hz", type=float, default=10.0)
    observer.add_argument("--html", type=Path)

    subparsers.add_parser("self-test", help="check pure simulation invariants")
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> BoidsConfig:
    """Build and validate a world configuration from CLI arguments."""
    config = BoidsConfig(
        width=args.width,
        height=args.height,
        perception_radius=args.perception,
        separation_radius=args.separation_radius,
        separation_weight=args.separation_weight,
        alignment_weight=args.alignment_weight,
        cohesion_weight=args.cohesion_weight,
        max_speed=args.max_speed,
        max_acceleration=args.max_acceleration,
        time_step=args.time_step,
    )
    positive_values = (
        config.width,
        config.height,
        config.perception_radius,
        config.separation_radius,
        config.max_speed,
        config.max_acceleration,
        config.time_step,
    )
    if any(value <= 0.0 for value in positive_values):
        raise SystemExit(
            "world sizes, radii, limits, and time step must be positive"
        )
    if config.separation_radius > config.perception_radius:
        raise SystemExit("separation radius cannot exceed perception radius")
    return config


def validate_run_arguments(args: argparse.Namespace) -> None:
    """Reject invalid timing and recording arguments."""
    if args.command in {"local", "node"}:
        if args.steps < 0:
            raise SystemExit("steps cannot be negative")
        if args.record_every <= 0:
            raise SystemExit("record-every must be positive")
    if args.command in {"node", "observe"}:
        if args.hz <= 0.0:
            raise SystemExit("hz must be positive")
        if args.stale_after <= 0.0:
            raise SystemExit("stale-after must be positive")
        if not args.topic:
            raise SystemExit("topic cannot be empty")
    if args.command == "node":
        if not 0 <= args.node_id < 2_000:
            raise SystemExit("node-id must be in the range 0..1999")
        if args.discovery_wait < 0.0:
            raise SystemExit("discovery-wait cannot be negative")
        if args.report_every <= 0.0:
            raise SystemExit("report-every must be positive")
    if args.command == "observe" and args.seconds <= 0.0:
        raise SystemExit("seconds must be positive")


def main() -> None:
    """Run the selected lab mode."""
    args = parse_args()
    if args.command == "self-test":
        run_self_test()
        return

    config = config_from_args(args)
    validate_run_arguments(args)
    if args.command == "local":
        run_local(args, config)
    elif args.command == "node":
        run_node(args, config)
    elif args.command == "observe":
        run_observer(args, config)
    else:
        raise AssertionError(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
