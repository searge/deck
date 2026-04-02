# %%
# @title Exponential Weighted Moving Average
# Load average as the kernel computes it — EWMA over the run queue length.

# %%
# @title Imports & core functions
from dataclasses import dataclass
from functools import reduce
from itertools import accumulate
from math import exp

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

SAMPLE_INTERVAL_SECONDS = 5  # kernel samples run queue every 5 s


@dataclass(frozen=True)
class LoadWindow:
    label: str
    window_seconds: int
    load: float = 0.0


def decay_factor(window_seconds: int) -> float:
    return exp(-SAMPLE_INTERVAL_SECONDS / window_seconds)


def next_load(window: LoadWindow, runnable_processes: int) -> LoadWindow:
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
    return tuple(next_load(window, runnable_processes) for window in windows)


# %%
# @title Run queue samples
# 60 samples × 5 s = 5 minutes of observed run queue.
# /app/worker dominates — typical for a containerised service under load.

SAMPLES = 60
rng = np.random.default_rng(seed=42)

# Background processes: Poisson arrivals — realistic for low, stable load.
background: dict[str, np.ndarray] = {
    "kworker":  rng.poisson(lam=0.5, size=SAMPLES),
    "sshd":     rng.poisson(lam=1.0, size=SAMPLES),
    "postgres": rng.poisson(lam=1.5, size=SAMPLES),
    "nginx":    rng.poisson(lam=2.0, size=SAMPLES),
}

# /app/worker: Gaussian spike centered at t=30 (midpoint of the 5-min window).
# Width (σ=8) gives ~80 s ramp-up and ramp-down — realistic for a traffic burst.
t = np.arange(SAMPLES)
spike_shape = np.exp(-0.5 * ((t - SAMPLES // 2) / 8) ** 2)
app_worker = np.round(spike_shape * 10).astype(int)

runnable_by_process = background | {"/app/worker": app_worker}

# Total runnable processes per sample — this is what the kernel sees.
runnable_per_sample: np.ndarray = np.sum(list(runnable_by_process.values()), axis=0)


# %%
# @title Simulate
LOAD_WINDOWS = (
    LoadWindow("1min",  window_seconds=60),
    LoadWindow("5min",  window_seconds=300),
    LoadWindow("15min", window_seconds=900),
)

# final state — like Haskell's foldl
final = reduce(step, runnable_per_sample.tolist(), LOAD_WINDOWS)

# full history — like Haskell's scanl
history = list(accumulate(runnable_per_sample.tolist(), step, initial=LOAD_WINDOWS))


# %%
# @title Interpret: CPU utilization
CPU_COUNT = 12  # 12 has the most divisors under 16: 1, 2, 3, 4, 6, 12


def cpu_utilization(load: float, cpu_count: int) -> float:
    return load / cpu_count * 100


def load_state(utilization_percent: float) -> str:
    if utilization_percent < 70:
        return "healthy"
    if utilization_percent <= 100:
        return "saturated"
    return "overloaded"


def report(label: str, windows: tuple[LoadWindow, ...]) -> None:
    print(label)
    for window in windows:
        utilization = cpu_utilization(window.load, CPU_COUNT)
        print(f"  {window.label:>5}  LA={window.load:5.2f}  {utilization:6.1f}%  {load_state(utilization)}")


peak_index = int(np.argmax(runnable_per_sample))

report("at peak:", history[peak_index])
report("after 5 min:", final)

# %%
# @title Plot
time_seconds = np.arange(len(history)) * SAMPLE_INTERVAL_SECONDS

# history[0] is the initial state (all zeros), so prepend 0 to align run queue
run_queue = np.concatenate([[0], runnable_per_sample])

la_by_window = {
    window.label: [state[i].load for state in history]
    for i, window in enumerate(LOAD_WINDOWS)
}

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    subplot_titles=("Run queue (runnable processes)", "Load average by window"),
    vertical_spacing=0.12,
)

fig.add_trace(
    go.Scatter(x=time_seconds, y=run_queue, name="runnable", fill="tozeroy"),
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
    y0=CPU_COUNT, y1=CPU_COUNT, yref="y2",
    line={"dash": "dash", "color": "red"},
)
fig.add_annotation(
    x=1, xref="x2 domain",
    y=CPU_COUNT, yref="y2",
    text=f"saturation (LA = {CPU_COUNT} = nCPU)",
    showarrow=False,
    xanchor="right",
    yanchor="bottom",
)

fig.update_xaxes(title_text="time (s)", row=2, col=1)
fig.update_yaxes(title_text="processes", row=1, col=1)
fig.update_yaxes(title_text="load average", row=2, col=1)
fig.update_layout(title="EWMA load average — 5-minute traffic spike")

fig.show()

# %%
