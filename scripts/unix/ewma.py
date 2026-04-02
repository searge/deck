# %%
"""Exponential Weighted Moving Average — Linux load average simulation.

Demonstrates how the kernel computes the 1-, 5-, and 15-minute load averages
using EWMA over the run queue length, sampled every 5 seconds.
"""

# %%
# @title Imports & constants
from dataclasses import dataclass
from functools import reduce
from itertools import accumulate
from math import exp

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

SAMPLE_INTERVAL_SECONDS: int = 5
"""Kernel samples the run queue every 5 seconds."""

SAMPLES: int = 60
"""Number of samples: 60 × 5 s = 5 minutes."""

CPU_COUNT: int = 12
"""Logical CPU count. 12 has many divisors, making mental math easy."""


# %%
# @title Core EWMA


@dataclass(frozen=True)
class LoadWindow:
    """An immutable snapshot of one EWMA load average window.

    Attributes:
        label: Human-readable name — "1min", "5min", or "15min".
        window_seconds: Window duration in seconds.
        load: Current EWMA value.
    """

    label: str
    window_seconds: int
    load: float = 0.0


LOAD_WINDOWS: tuple[LoadWindow, ...] = (
    LoadWindow("1min", window_seconds=60),
    LoadWindow("5min", window_seconds=300),
    LoadWindow("15min", window_seconds=900),
)


def decay_factor(window_seconds: int) -> float:
    """Return the EWMA decay factor α = e^(-Δt/T) for a given window.

    Args:
        window_seconds: Window duration T in seconds.

    Returns:
        Weight assigned to past observations at each sample step.
    """
    return exp(-SAMPLE_INTERVAL_SECONDS / window_seconds)


def next_load(window: LoadWindow, runnable_processes: int) -> LoadWindow:
    """Advance one window by one sample.

    Args:
        window: Current window state.
        runnable_processes: Number of processes in R/D state at this sample.

    Returns:
        New window with updated EWMA load.
    """
    alpha = decay_factor(window.window_seconds)
    return LoadWindow(
        label=window.label,
        window_seconds=window.window_seconds,
        load=window.load * alpha + runnable_processes * (1 - alpha),
    )


def step(
    windows: tuple[LoadWindow, ...],
    runnable_processes: int,
) -> tuple[LoadWindow, ...]:
    """Advance all windows by one sample — the kernel's per-tick update.

    Args:
        windows: Current state of all load windows.
        runnable_processes: Run queue length at this sample.

    Returns:
        Updated tuple of all windows.
    """
    return tuple(next_load(window, runnable_processes) for window in windows)


# %%
# @title Run queue


def build_process_queues(
    samples: int, rng: np.random.Generator
) -> dict[str, np.ndarray]:
    """Generate per-process run queue traces with a Gaussian traffic spike.

    Background processes use Poisson arrivals. The application worker
    produces a Gaussian spike centred at the midpoint of the window —
    typical shape for a short traffic burst.

    Args:
        samples: Total number of 5-second samples.
        rng: NumPy random generator (pass a seeded one for reproducibility).

    Returns:
        Mapping of process name to its run queue trace (one value per sample).
    """
    # Background processes: Poisson arrivals — realistic for stable, low load.
    background: dict[str, np.ndarray] = {
        "kworker":  rng.poisson(lam=0.5, size=samples),
        "sshd":     rng.poisson(lam=1.0, size=samples),
        "postgres": rng.poisson(lam=1.5, size=samples),
        "nginx":    rng.poisson(lam=2.0, size=samples),
    }

    # /app/worker: Gaussian spike centred at the midpoint.
    # σ=8 samples (40 s) gives a realistic ~80-second ramp-up and ramp-down.
    indices = np.arange(samples)
    center = samples // 2
    spike_shape = np.exp(-0.5 * ((indices - center) / 8) ** 2)
    app_worker = np.round(spike_shape * 10).astype(int)

    return background | {"/app/worker": app_worker}


def total_run_queue(by_process: dict[str, np.ndarray]) -> np.ndarray:
    """Sum per-process queues into a single trace — what the kernel sees.

    Args:
        by_process: Per-process run queue traces from `build_process_queues`.

    Returns:
        1-D integer array of total runnable process counts, one per sample.
    """
    return np.sum(list(by_process.values()), axis=0)


rng = np.random.default_rng(seed=42)
runnable_by_process = build_process_queues(SAMPLES, rng)
runnable_per_sample = total_run_queue(runnable_by_process)


# %%
# @title Simulate


def simulate(
    runnable_per_sample: np.ndarray,
    initial_windows: tuple[LoadWindow, ...],
) -> tuple[tuple[LoadWindow, ...], list[tuple[LoadWindow, ...]]]:
    """Run the EWMA simulation over the full sample trace.

    Args:
        runnable_per_sample: Run queue length at each sample step.
        initial_windows: Starting state — typically all loads set to 0.

    Returns:
        A tuple of (final_state, history) where history contains the window
        state after every sample, including the initial state at index 0.
        Mirrors Haskell's (foldl, scanl) over the same input.
    """
    samples = runnable_per_sample.tolist()
    final = reduce(step, samples, initial_windows)
    history = list(accumulate(samples, step, initial=initial_windows))
    return final, history


final, history = simulate(runnable_per_sample, LOAD_WINDOWS)


# %%
# @title Interpret


def cpu_utilization(load: float, cpu_count: int) -> float:
    """Return load as a percentage of total CPU capacity.

    Args:
        load: Raw EWMA load average value.
        cpu_count: Number of logical CPUs (from `nproc`).

    Returns:
        Utilization in percent: 100 % means all CPUs are fully saturated.
    """
    return load / cpu_count * 100


def load_state(utilization_percent: float) -> str:
    """Classify utilization into a human-readable load state.

    Args:
        utilization_percent: Value returned by `cpu_utilization`.

    Returns:
        "healthy" below 70 %, "saturated" up to 100 %, "overloaded" above.
    """
    if utilization_percent < 70:
        return "healthy"
    if utilization_percent <= 100:
        return "saturated"
    return "overloaded"


def report(
    label: str, windows: tuple[LoadWindow, ...], cpu_count: int
) -> None:
    """Print a formatted load average report for a set of windows.

    Args:
        label: Header line printed before the window rows.
        windows: Window states to report.
        cpu_count: Number of logical CPUs used for utilization calculation.
    """
    print(label)
    for window in windows:
        utilization = cpu_utilization(window.load, cpu_count)
        state = load_state(utilization)
        print(f"  {window.label:>5}  LA={window.load:5.2f}  {utilization:6.1f}%  {state}")


peak_index = int(np.argmax(runnable_per_sample))

report("at peak:", history[peak_index], CPU_COUNT)
report("after 5 min:", final, CPU_COUNT)


# %%
# @title Process snapshot (htop-style)


def build_htop_figure(
    by_process: dict[str, np.ndarray],
    peak_index: int,
    cpu_count: int,
) -> go.Figure:
    """Build an htop-style horizontal bar chart at the peak moment.

    Processes are sorted descending by run queue length at peak.
    Bar colour reflects load state: green → healthy, yellow → saturated,
    red → overloaded (relative to cpu_count).

    Args:
        by_process: Per-process run queue traces from `build_process_queues`.
        peak_index: Sample index of the peak — use np.argmax on total queue.
        cpu_count: Number of logical CPUs, used to colour the bars.

    Returns:
        Plotly Figure ready to display or export.
    """
    snapshot = {
        name: int(counts[peak_index])
        for name, counts in by_process.items()
    }
    snapshot = dict(sorted(snapshot.items(), key=lambda item: item[1]))

    def bar_color(count: int) -> str:
        utilization = count / cpu_count * 100
        if utilization < 70:
            return "#88c0d0"   # blue-ish — healthy
        if utilization <= 100:
            return "#ebcb8b"   # yellow — saturated
        return "#bf616a"       # red — overloaded

    peak_time_seconds = peak_index * SAMPLE_INTERVAL_SECONDS

    fig = go.Figure(go.Bar(
        x=list(snapshot.values()),
        y=list(snapshot.keys()),
        orientation="h",
        marker_color=[bar_color(v) for v in snapshot.values()],
        text=list(snapshot.values()),
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Run queue snapshot at peak (t = {peak_time_seconds} s)",
        xaxis_title="runnable processes",
        xaxis={"range": [0, max(snapshot.values()) + 2]},
        height=300,
    )
    return fig


htop_fig = build_htop_figure(runnable_by_process, peak_index, CPU_COUNT)
htop_fig.show()


# %%
# @title Plot


def build_figure(
    runnable_per_sample: np.ndarray,
    history: list[tuple[LoadWindow, ...]],
    load_windows: tuple[LoadWindow, ...],
    cpu_count: int,
) -> go.Figure:
    """Build a two-panel Plotly figure showing run queue and load averages.

    Top panel: raw run queue trace.
    Bottom panel: EWMA load average for each window, with a saturation line.

    Args:
        runnable_per_sample: Run queue length at each sample step.
        history: Full simulation history from `simulate`.
        load_windows: Window definitions used in the simulation.
        cpu_count: Number of logical CPUs — drawn as the saturation threshold.

    Returns:
        Plotly Figure ready to display or export.
    """
    # history[0] is the initial state (all zeros), prepend 0 to align axes
    time_seconds = np.arange(len(history)) * SAMPLE_INTERVAL_SECONDS
    run_queue = np.concatenate([[0], runnable_per_sample])

    la_by_window = {
        window.label: [state[i].load for state in history]
        for i, window in enumerate(load_windows)
    }

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=(
            "Run queue (runnable processes)",
            "Load average by window",
        ),
        vertical_spacing=0.12,
    )

    fig.add_trace(
        go.Scatter(
            x=time_seconds, y=run_queue, name="runnable", fill="tozeroy"
        ),
        row=1, col=1,
    )

    for label, values in la_by_window.items():
        fig.add_trace(
            go.Scatter(x=time_seconds, y=values, name=label),
            row=2, col=1,
        )

    fig.add_shape(
        type="line",
        x0=0, x1=1, xref="x2 domain",
        y0=cpu_count, y1=cpu_count, yref="y2",
        line={"dash": "dash", "color": "red"},
    )
    fig.add_annotation(
        x=1, xref="x2 domain",
        y=cpu_count, yref="y2",
        text=f"saturation (LA = {cpu_count} = nCPU)",
        showarrow=False,
        xanchor="right",
        yanchor="bottom",
    )

    fig.update_xaxes(title_text="time (s)", row=2, col=1)
    fig.update_yaxes(title_text="processes", row=1, col=1)
    fig.update_yaxes(title_text="load average", row=2, col=1)
    fig.update_layout(
        title="EWMA load average — 5-minute traffic spike",
        legend={
            "orientation": "h",
            "yanchor": "top", "y": -0.25,
            "xanchor": "center", "x": 0.5,
        },
        margin={"b": 100},
    )

    return fig


fig = build_figure(runnable_per_sample, history, LOAD_WINDOWS, CPU_COUNT)
fig.show()
