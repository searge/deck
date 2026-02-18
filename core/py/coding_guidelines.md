---
tags:
  - python
  - architecture
  - guidelines
aliases:
  - Coding Guidelines
title: Coding Guidelines
description: Functional Python guidelines — pure functions, frozen dataclasses, layered architecture, and typing rules.
---

# Coding Guidelines

Guidelines for Python CLI tools aimed at platform engineering and
sysadmin work. The core idea: functional approach + dataclasses makes
code easier to understand, test, and maintain — especially for people
who write Python occasionally, not daily.

This document can be copied into any project as `docs/CODING_GUIDELINES.md`
or referenced from `CLAUDE.md`.

## Why functional

Classes add cognitive load. A function that takes data and returns data
is the simplest unit of code to reason about. You can test it without
mocking, compose it without inheritance, and read it without tracing
state through method calls.

The admin who hasn't touched the codebase in 3 months will understand
`result = analyze(data, config)` faster than figuring out which
combination of methods on which objects produces the same result.

## Core principles

1. **Functions over classes** — classes only for data (`@dataclass(frozen=True)`)
2. **Immutable data** — frozen dataclasses, NamedTuples, `dataclasses.replace()` for updates
3. **Pure logic, impure edges** — keep side effects at the boundary (CLI, config)
4. **Config loaded once** — frozen dataclass created at startup, passed down the call chain
5. **Type everything** — mypy strict mode, no `Any` unless wrapping external APIs
6. **Small files** — 100-250 lines per module; split when it grows

## Architecture

### Principle

Side effects live at the edges. Pure logic lives in the middle. Start
flat — add layers only when the project grows (see [project_skeleton](project_skeleton.md)).

```text
CLI (side effects: user IO, exit codes)
 ↓
Pure logic (no IO, no imports from external systems)
 ↓
External systems (API, DB, subprocess, filesystem)
```

**Dependency direction is inward only.** Logic never imports from
external system modules or CLI.

### What goes where

| Concern                | Does                                         | Examples                        |
| ---------------------- | -------------------------------------------- | ------------------------------- |
| **CLI**                | Parse args, load config, format output       | Typer commands, Rich tables     |
| **Logic**              | Business rules, data transformation          | Parsing, filtering, analysis    |
| **External systems**   | Talk to the outside world                    | httpx client, subprocess, DB    |
| **Config**             | Load environment once, return frozen struct  | `load_config()` in `config.py`  |

## Data modeling

### Frozen dataclasses

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PodInfo:
    name: str
    namespace: str
    cpu_request: int         # millicores
    memory_request: int      # bytes
    labels: tuple[str, ...]  # tuples, not lists (hashable)
    issues: tuple[str, ...] = field(default_factory=tuple)
```

Rules:

- Always `frozen=True` — mutable dataclasses are a source of bugs
- Use `tuple` instead of `list` for collection fields (hashable, truly immutable)
- Use `dataclasses.replace()` to create modified copies
- Properties are fine for computed values
- Methods are fine for data access (`.is_critical()`, `.to_dict()`)
- **No logic methods** — keep analysis in functions

### NamedTuples for compact records

```python
from typing import NamedTuple


class MetricPoint(NamedTuple):
    timestamp: float
    value: float
    label: str
```

Use NamedTuples when you need:

- Lightweight records (no default values needed)
- Dict key capability (always hashable)
- Tuple unpacking

### Pydantic for API boundaries

```python
from pydantic import BaseModel, ConfigDict


class TicketResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    title: str
    status: int
    date_creation: str
```

Use Pydantic when:

- Validating external input (API responses, CSV rows, user input)
- Serialization/deserialization is needed

Don't use Pydantic for internal data — frozen dataclasses are lighter.

## Functions

### Pure functions

A pure function:

- Returns the same output for the same input
- Has no side effects (no IO, no mutation, no logging)
- Is trivially testable

```python
# Good: pure
def calculate_cpu_percent(used: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(used / total * 100, 1)

# Bad: impure (calls subprocess)
def get_cpu_percent() -> float:
    output = subprocess.check_output(["nproc"])
    ...
```

### Function signatures

```python
def analyze_pod(
    pod: PodInfo,
    *,                          # keyword-only after this
    threshold_cpu: int = 80,
    threshold_mem: int = 90,
) -> AnalysisResult:
```

- Use keyword-only arguments (`*`) for anything beyond the main input
- Return typed results, not dicts (except at serialization boundaries)
- Keep functions short: 20-50 lines, one level of abstraction

### Composition over nesting

```python
# Good: pipeline
raw = fetch_pods(config)
pods = [parse_pod(p) for p in raw]
filtered = [p for p in pods if not is_system_namespace(p.namespace)]
result = analyze_workload(filtered, config.thresholds)

# Bad: nested
result = analyze_workload(
    [parse_pod(p) for p in fetch_pods(config)
     if not is_system_namespace(parse_pod(p).namespace)],
    config.thresholds,
)
```

### Lazy evaluation

Use generators for memory-efficient filtering:

```python
def filter_active(pods: Iterable[PodInfo]) -> Iterable[PodInfo]:
    for pod in pods:
        if pod.status == "Running":
            yield pod
```

Materialize only when you need the full list: `list(filter_active(pods))`.

## Configuration

### Pattern

```python
@dataclass(frozen=True)
class Config:
    api_url: str
    api_token: str
    timeout: int = 30


def load_config() -> Config:
    """Load from environment. Fail fast on missing values."""
    load_dotenv()
    return Config(
        api_url=os.environ["APP_API_URL"],
        api_token=os.environ["APP_API_TOKEN"],
    )
```

### Rules

- **One load point** — `load_config()` called once in CLI, result passed everywhere
- **Environment access only in config.py** — other modules receive config, never read env
- **Fail fast** — `os.environ["KEY"]` raises `KeyError` for missing values

## Subprocess

```python
import shlex
import subprocess


def kubectl_json(command: str) -> dict:
    """Run kubectl and return parsed JSON."""
    args = shlex.split(f"kubectl {command} -o json")
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
```

Rules:

- **Never `shell=True`** — use `shlex.split()` or argument lists
- **Keep subprocess calls separate** from pure logic
- **Wrap errors** — catch `subprocess.CalledProcessError`, raise meaningful exceptions

## Error handling

| Concern              | Pattern                                                                 |
| -------------------- | ----------------------------------------------------------------------- |
| **External systems** | Typed exceptions: `KubectlError`, `ApiError`                            |
| **Logic**            | Return error data in result types; raise `ValueError` for invalid input |
| **CLI**              | Map to exit codes (0 = ok, 1 = user error, 2 = runtime error)           |

## Typing

### Python 3.13+ style

```python
# Built-in generics (no imports needed)
def process(items: list[str]) -> dict[str, int]: ...

# Union with |
def get_value(key: str) -> str | None: ...

# Type aliases
type NodeName = str
type Millicores = int
```

### mypy strict mode

```toml
[tool.mypy]
python_version = "3.13"
disallow_untyped_defs = true
disallow_incomplete_defs = true
warn_return_any = true
warn_unused_configs = true
```

Every function must have full type annotations. No exceptions.

## Testing

### Pure functions = trivial tests

```python
def test_cpu_percent():
    assert calculate_cpu_percent(80, 100) == 80.0
    assert calculate_cpu_percent(0, 100) == 0.0
    assert calculate_cpu_percent(0, 0) == 0.0

def test_pod_analysis():
    pod = PodInfo(name="web", namespace="default", cpu_request=500, memory_request=512_000_000, labels=())
    result = analyze_pod(pod, threshold_cpu=80)
    assert result.status == "ok"
```

No mocking needed for pure logic. Mock only external calls
(subprocess, HTTP) when testing integration.

## Code style

### Naming

- `snake_case` for everything (files, functions, variables)
- Constants: `UPPER_CASE`
- Frozen dataclasses: `PascalCase`
- Functions: verb-first (`parse_pod`, `filter_active`, `calculate_score`)

### File size

Split when a module exceeds ~250 lines. Signs it's time:

- Multiple unrelated functions
- Two or more "sections" separated by comments
- Imports from more than 5 modules

## What to avoid

| Don't                                     | Do instead                       |
| ----------------------------------------- | -------------------------------- |
| Mutable dataclass                         | `@dataclass(frozen=True)`        |
| Class with only `__init__` and one method | Function                         |
| `self.config = config` in every method    | Pass config as argument          |
| `os.getenv()` scattered around            | `config.py` loads once           |
| `shell=True`                              | `shlex.split()`                  |
| Bare `dict` for structured data           | Frozen dataclass                 |
| `from __future__ import annotations`      | Python 3.13 builtins             |
| Deep inheritance                          | Function composition             |
| God-class (>300 lines, >10 methods)       | Split into functions + dataclass |

## See also

- [project_skeleton](project_skeleton.md)

## References

- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Mypy documentation](https://mypy.readthedocs.io/)
- [Ruff linter](https://docs.astral.sh/ruff/)
- [Typer CLI framework](https://typer.tiangolo.com/)
- [Architecture Patterns with Python](https://www.cosmicpython.com/) — Harry Percival & Bob Gregory
