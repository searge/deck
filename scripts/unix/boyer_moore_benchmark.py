#!/usr/bin/env python3
"""Benchmark Boyer-Moore against naive, built-in, and CLI literal search."""

import argparse
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter_ns

import plotly.graph_objects as go
from plotly.subplots import make_subplots

type Search = Callable[[], int]


@dataclass(frozen=True)
class CompiledPattern:
    """Boyer-Moore lookup tables for one non-empty byte pattern."""

    pattern: bytes
    bad_character: tuple[int, ...]
    good_suffix: tuple[int, ...]


@dataclass(frozen=True)
class SearchStats:
    """Algorithm work performed before the first match."""

    index: int
    alignments: int
    comparisons: int


@dataclass(frozen=True)
class Scenario:
    """One deterministic corpus and the expected first match."""

    name: str
    description: str
    text: bytes
    pattern: bytes
    expected_index: int


@dataclass(frozen=True)
class Benchmark:
    """Median runtime and normalized throughput for one search method."""

    method: str
    scope: str
    seconds: float
    mib_per_second: float


@dataclass(frozen=True)
class ScenarioResult:
    """Benchmarks and operation counts for one scenario."""

    scenario: Scenario
    benchmarks: tuple[Benchmark, ...]
    naive_stats: SearchStats
    boyer_moore_stats: SearchStats
    preprocess_microseconds: float


class Arguments(argparse.Namespace):
    """Typed command-line arguments populated by argparse."""

    def __init__(self) -> None:
        super().__init__()
        self.size_mib = 2.0
        self.repeats = 3
        self.skip_cli = False
        self.html: Path | None = None
        self.show = False


PARAGRAPH = (
    b"a scheduler records desired state while workers report observed state. "
    b"replicas exchange heartbeats, append log entries, and recover after "
    b"partial failure. operators search traces for the first causal event.\n"
)
TYPICAL_PATTERN = b"QUORUM_RECOVERY_SEQUENCE_42"
ADVERSARIAL_PATTERN = b"a" * 31 + b"b"


# %%
# @title Preprocessing


def build_bad_character_table(pattern: bytes) -> tuple[int, ...]:
    """Map every byte to its rightmost position in the pattern."""
    table = [-1] * 256
    for index, value in enumerate(pattern):
        table[value] = index
    return tuple(table)


def build_good_suffix_table(pattern: bytes) -> tuple[int, ...]:
    """Build strong good-suffix shifts, including matched-prefix fallback."""
    length = len(pattern)
    shifts = [0] * (length + 1)
    borders = [0] * (length + 1)

    left = length
    right = length + 1
    borders[left] = right
    while left > 0:
        while right <= length and pattern[left - 1] != pattern[right - 1]:
            if shifts[right] == 0:
                shifts[right] = right - left
            right = borders[right]
        left -= 1
        right -= 1
        borders[left] = right

    right = borders[0]
    for index in range(length + 1):
        if shifts[index] == 0:
            shifts[index] = right
        if index == right:
            right = borders[right]

    return tuple(shifts)


def compile_pattern(pattern: bytes) -> CompiledPattern:
    """Precompute both Boyer-Moore shift tables."""
    if not pattern:
        raise ValueError("Boyer-Moore pattern must not be empty")
    return CompiledPattern(
        pattern=pattern,
        bad_character=build_bad_character_table(pattern),
        good_suffix=build_good_suffix_table(pattern),
    )


# %%
# @title Search algorithms


def naive_search(text: bytes, pattern: bytes) -> int:
    """Return the first match using left-to-right alignment checks."""
    if not pattern:
        return 0
    limit = len(text) - len(pattern)
    for offset in range(limit + 1):
        pattern_index = 0
        while (
            pattern_index < len(pattern)
            and text[offset + pattern_index] == pattern[pattern_index]
        ):
            pattern_index += 1
        if pattern_index == len(pattern):
            return offset
    return -1


def boyer_moore_search(text: bytes, compiled: CompiledPattern) -> int:
    """Return the first match using bad-character and good-suffix shifts."""
    pattern = compiled.pattern
    offset = 0
    limit = len(text) - len(pattern)

    while offset <= limit:
        pattern_index = len(pattern) - 1
        while (
            pattern_index >= 0
            and pattern[pattern_index] == text[offset + pattern_index]
        ):
            pattern_index -= 1
        if pattern_index < 0:
            return offset

        bad_character_shift = (
            pattern_index
            - compiled.bad_character[text[offset + pattern_index]]
        )
        good_suffix_shift = compiled.good_suffix[pattern_index + 1]
        offset += max(1, bad_character_shift, good_suffix_shift)

    return -1


def naive_search_stats(text: bytes, pattern: bytes) -> SearchStats:
    """Return naive result plus alignment and comparison counts."""
    if not pattern:
        return SearchStats(0, 1, 0)
    limit = len(text) - len(pattern)
    alignments = 0
    comparisons = 0
    for offset in range(limit + 1):
        alignments += 1
        pattern_index = 0
        while pattern_index < len(pattern):
            comparisons += 1
            if text[offset + pattern_index] != pattern[pattern_index]:
                break
            pattern_index += 1
        if pattern_index == len(pattern):
            return SearchStats(offset, alignments, comparisons)
    return SearchStats(-1, alignments, comparisons)


def boyer_moore_search_stats(
    text: bytes,
    compiled: CompiledPattern,
) -> SearchStats:
    """Return Boyer-Moore result plus alignment and comparison counts."""
    pattern = compiled.pattern
    offset = 0
    limit = len(text) - len(pattern)
    alignments = 0
    comparisons = 0

    while offset <= limit:
        alignments += 1
        pattern_index = len(pattern) - 1
        while pattern_index >= 0:
            comparisons += 1
            if pattern[pattern_index] != text[offset + pattern_index]:
                break
            pattern_index -= 1
        if pattern_index < 0:
            return SearchStats(offset, alignments, comparisons)

        bad_character_shift = (
            pattern_index
            - compiled.bad_character[text[offset + pattern_index]]
        )
        good_suffix_shift = compiled.good_suffix[pattern_index + 1]
        offset += max(1, bad_character_shift, good_suffix_shift)

    return SearchStats(-1, alignments, comparisons)


# %%
# @title Corpora


def build_typical_scenario(size_bytes: int) -> Scenario:
    """Build varied ASCII text with one long literal at the end."""
    if size_bytes <= len(TYPICAL_PATTERN):
        raise ValueError("typical corpus must be larger than its pattern")
    if TYPICAL_PATTERN in PARAGRAPH:
        raise AssertionError("typical pattern must be absent from base text")

    prefix_size = size_bytes - len(TYPICAL_PATTERN)
    repeats = prefix_size // len(PARAGRAPH) + 1
    text = (PARAGRAPH * repeats)[:prefix_size] + TYPICAL_PATTERN
    return Scenario(
        name="typical",
        description="varied ASCII, long pattern absent until EOF",
        text=text,
        pattern=TYPICAL_PATTERN,
        expected_index=prefix_size,
    )


def build_adversarial_scenario(size_bytes: int) -> Scenario:
    """Build a small-alphabet corpus that forces one-byte shifts."""
    if size_bytes <= len(ADVERSARIAL_PATTERN):
        raise ValueError("adversarial corpus must be larger than its pattern")
    prefix_size = size_bytes - len(ADVERSARIAL_PATTERN)
    text = b"a" * prefix_size + ADVERSARIAL_PATTERN
    return Scenario(
        name="adversarial",
        description="one-byte alphabet, repeated suffix, match at EOF",
        text=text,
        pattern=ADVERSARIAL_PATTERN,
        expected_index=prefix_size,
    )


# %%
# @title Timing


def median_seconds(
    operation: Callable[[], object],
    repeats: int,
) -> float:
    """Warm once, then return the median wall-clock duration."""
    operation()
    samples = []
    for _ in range(repeats):
        started = perf_counter_ns()
        operation()
        samples.append((perf_counter_ns() - started) / 1_000_000_000)
    return median(samples)


def benchmark_search(
    method: str,
    scope: str,
    operation: Search,
    expected_index: int,
    size_bytes: int,
    repeats: int,
) -> Benchmark:
    """Validate a search operation and measure median throughput."""
    actual_index = operation()
    if actual_index != expected_index:
        raise AssertionError(
            f"{method} returned {actual_index}, expected {expected_index}"
        )
    seconds = median_seconds(operation, repeats)
    size_mib = size_bytes / 1024**2
    return Benchmark(method, scope, seconds, size_mib / seconds)


def benchmark_command(
    method: str,
    command: tuple[str, ...],
    size_bytes: int,
    repeats: int,
) -> Benchmark:
    """Measure a successful CLI search including process and file overhead."""
    environment = os.environ | {"LC_ALL": "C"}

    def run() -> int:
        completed = subprocess.run(
            command,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            error = completed.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"{method} failed: {error}")
        return 0

    seconds = median_seconds(run, repeats)
    size_mib = size_bytes / 1024**2
    return Benchmark(method, "file + process", seconds, size_mib / seconds)


def benchmark_preprocessing(pattern: bytes) -> float:
    """Return median pattern compilation time in microseconds."""
    seconds = median_seconds(lambda: compile_pattern(pattern), repeats=101)
    return seconds * 1_000_000


def benchmark_scenario(
    scenario: Scenario,
    repeats: int,
    include_cli: bool,
) -> ScenarioResult:
    """Run all available methods against one deterministic corpus."""
    compiled = compile_pattern(scenario.pattern)
    benchmarks = [
        benchmark_search(
            "naive Python",
            "memory",
            lambda: naive_search(scenario.text, scenario.pattern),
            scenario.expected_index,
            len(scenario.text),
            repeats,
        ),
        benchmark_search(
            "Boyer-Moore Python",
            "memory",
            lambda: boyer_moore_search(scenario.text, compiled),
            scenario.expected_index,
            len(scenario.text),
            repeats,
        ),
        benchmark_search(
            "bytes.find",
            "memory (C)",
            lambda: scenario.text.find(scenario.pattern),
            scenario.expected_index,
            len(scenario.text),
            repeats,
        ),
    ]

    if include_cli:
        with tempfile.TemporaryDirectory(prefix="boyer-moore-") as temp_dir:
            corpus_path = Path(temp_dir) / f"{scenario.name}.txt"
            corpus_path.write_bytes(scenario.text)
            pattern = scenario.pattern.decode("ascii")

            grep = shutil.which("grep")
            if grep:
                benchmarks.append(
                    benchmark_command(
                        "grep -F",
                        (
                            grep,
                            "-F",
                            "-m",
                            "1",
                            "-q",
                            "--",
                            pattern,
                            str(corpus_path),
                        ),
                        len(scenario.text),
                        repeats,
                    )
                )

            ripgrep = shutil.which("rg")
            if ripgrep:
                benchmarks.append(
                    benchmark_command(
                        "rg -F",
                        (
                            ripgrep,
                            "--fixed-strings",
                            "--max-count",
                            "1",
                            "--quiet",
                            "--no-config",
                            "--",
                            pattern,
                            str(corpus_path),
                        ),
                        len(scenario.text),
                        repeats,
                    )
                )

    return ScenarioResult(
        scenario=scenario,
        benchmarks=tuple(benchmarks),
        naive_stats=naive_search_stats(scenario.text, scenario.pattern),
        boyer_moore_stats=boyer_moore_search_stats(scenario.text, compiled),
        preprocess_microseconds=benchmark_preprocessing(scenario.pattern),
    )


# %%
# @title Report


def print_report(results: tuple[ScenarioResult, ...], repeats: int) -> None:
    """Print methodology, operation counts, and median throughput."""
    print(f"median of {repeats} warm-cache runs; first match is at EOF\n")
    for result in results:
        scenario = result.scenario
        size_mib = len(scenario.text) / 1024**2
        print(
            f"{scenario.name}: {size_mib:.3f} MiB, "
            f"pattern={len(scenario.pattern)} bytes"
        )
        print(f"  {scenario.description}")
        print(
            "  comparisons: "
            f"naive={result.naive_stats.comparisons:,}, "
            f"Boyer-Moore={result.boyer_moore_stats.comparisons:,}"
        )
        print(
            "  alignments : "
            f"naive={result.naive_stats.alignments:,}, "
            f"Boyer-Moore={result.boyer_moore_stats.alignments:,}"
        )
        print(f"  BM preprocessing: {result.preprocess_microseconds:.2f} us\n")
        print(
            f"  {'method':<20} {'scope':<16} {'median ms':>10} {'MiB/s':>12}"
        )
        print("  " + "-" * 62)
        for benchmark in result.benchmarks:
            print(
                f"  {benchmark.method:<20} {benchmark.scope:<16} "
                f"{benchmark.seconds * 1_000:>10.3f} "
                f"{benchmark.mib_per_second:>12.1f}"
            )
        print()


def build_figure(results: tuple[ScenarioResult, ...]) -> go.Figure:
    """Build one throughput chart per corpus scenario."""
    figure = make_subplots(
        rows=1,
        cols=len(results),
        subplot_titles=tuple(result.scenario.name for result in results),
        shared_yaxes=True,
    )
    colors = {
        "naive Python": "#bf616a",
        "Boyer-Moore Python": "#5e81ac",
        "bytes.find": "#a3be8c",
        "grep -F": "#ebcb8b",
        "rg -F": "#b48ead",
    }

    for column, result in enumerate(results, start=1):
        figure.add_trace(
            go.Bar(
                x=[benchmark.method for benchmark in result.benchmarks],
                y=[
                    benchmark.mib_per_second for benchmark in result.benchmarks
                ],
                marker_color=[
                    colors[benchmark.method] for benchmark in result.benchmarks
                ],
                text=[
                    f"{benchmark.mib_per_second:.1f}"
                    for benchmark in result.benchmarks
                ],
                textposition="outside",
                showlegend=False,
            ),
            row=1,
            col=column,
        )
        figure.update_xaxes(tickangle=-25, row=1, col=column)

    figure.update_yaxes(
        title_text="MiB/s - higher is better",
        type="log",
        row=1,
        col=1,
    )
    figure.update_layout(
        title="Literal search throughput by corpus",
        height=520,
        margin={"b": 120},
    )
    return figure


def parse_args() -> Arguments:
    """Parse benchmark size, repetition, and output options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--size-mib",
        type=float,
        default=2.0,
        help="size of the typical corpus (default: 2 MiB)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="timed repetitions after one warm-up (default: 3)",
    )
    parser.add_argument(
        "--skip-cli",
        action="store_true",
        help="skip grep and ripgrep subprocess benchmarks",
    )
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
    """Build corpora, run benchmarks, and render requested outputs."""
    args = parse_args()
    if args.size_mib <= 0:
        raise SystemExit("--size-mib must be positive")
    if args.repeats <= 0:
        raise SystemExit("--repeats must be positive")

    typical_size = max(64 * 1024, int(args.size_mib * 1024**2))
    adversarial_size = max(64 * 1024, min(typical_size // 16, 256 * 1024))
    scenarios = (
        build_typical_scenario(typical_size),
        build_adversarial_scenario(adversarial_size),
    )
    results = tuple(
        benchmark_scenario(scenario, args.repeats, not args.skip_cli)
        for scenario in scenarios
    )
    print_report(results, args.repeats)

    if args.html or args.show:
        figure = build_figure(results)
        if args.html:
            figure.write_html(args.html)
            print(f"wrote {args.html}")
        if args.show:
            figure.show()


if __name__ == "__main__":
    main()
