---
tags:
  - python
  - architecture
  - template
aliases:
  - Project Skeleton
title: Project Skeleton
description: Standard Python project layout for functional CLI tools — src layout, pyproject.toml, Taskfile, and skel.
---

# Project Skeleton

A minimal starting point for Python CLI tools that follow the functional
approach with frozen dataclasses. Scaffold new projects with:

```bash
# From root of the project
cd skel/
task python -- /
  '{"project_name":"my-tool","description":"What it does","target_dir":"~/Code/lrn/func/my-tool"}'
```

## Directory layout

What you get out of the box:

```text
project-name/
├── src/app_name/
│   ├── __init__.py
│   ├── __main__.py      # python -m app_name
│   ├── cli.py           # Typer app, commands
│   └── config.py        # Load once, frozen dataclass
├── tests/
│   └── test_placeholder.py
├── docs/
│   └── CODING_GUIDELINES.md
├── pyproject.toml
├── Taskfile.yaml
├── CLAUDE.md
├── README.md
├── .env.example
└── .gitignore
```

This is intentionally flat. Add subdirectories (`models/`, `domain/`,
`infrastructure/`) when the project grows — not before.

### When to refactor

**< 500 lines** — keep flat. `cli.py` + `config.py` + one or two modules.

**500-2000 lines** — split logic from side effects:

```text
src/app_name/
├── cli.py
├── config.py
├── models.py           # frozen dataclasses
├── core.py             # pure logic
└── client.py           # external systems
```

**2000+ lines** — directories by layer:

```text
src/app_name/
├── cli/
├── domain/
├── infrastructure/
├── models/
└── config.py
```

## pyproject.toml

```toml
[project]
name = "app-name"
version = "0.1.0"
description = "What this tool does"
requires-python = ">=3.13"
dependencies = [
    "typer>=0.23",
    "rich>=14",
    "python-dotenv",
]

[project.scripts]
app-name = "app_name.cli:app"

[tool.uv]
package = true

# --- Quality ---

[dependency-groups]
dev = [
    "mypy>=1.19",
    "ruff>=0.15",
    "ty",
    "pylint>=4",
    "pytest>=8",
]

[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "S", "B", "SIM", "RUF"]
ignore = ["S101", "UP040"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

No build-backend needed — `[tool.uv] package = true` is enough.

## Taskfile.yaml

```yaml
version: "3"

tasks:
  install:
    desc: Install dependencies
    cmds:
      - uv sync

  lint:
    desc: Format and lint
    cmds:
      - uv run ruff format src/ tests/
      - uv run ruff check --fix src/ tests/

  typecheck:
    desc: Static type checking
    cmds:
      - uv run mypy src/

  test:
    desc: Run all quality checks
    cmds:
      - task: lint
      - task: typecheck
      - uv run pytest

  app:
    desc: Run the application
    cmds:
      - uv run app-name {{.CLI_ARGS}}
```

## cli.py

```python
"""CLI entry point."""

import typer
from rich.console import Console

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="markdown",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


@app.callback()
def main() -> None:
    """What this tool does."""


@app.command()
def run() -> None:
    """Execute the main operation."""
    from app_name.config import load_config

    config = load_config()
    console.print(f"[green]app-name[/green] loaded with config: {config}")
```

`@app.callback()` makes `app-name` show help by default.
`@app.command()` defines subcommands — add more as the tool grows.

## config.py

```python
"""Configuration — load once, pass everywhere."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Application configuration. Immutable after creation."""

    project_root: Path
    # api_url: str
    # api_token: str


def load_config() -> Config:
    """Load config from environment. Fail fast on missing values."""
    load_dotenv()

    project_root = Path(__file__).resolve().parent.parent.parent

    return Config(
        project_root=project_root,
        # api_url=os.environ["APP_API_URL"],
        # api_token=os.environ["APP_API_TOKEN"],
    )
```

Uses `python-dotenv` to load `.env` file. Uncomment fields as needed —
`os.environ["KEY"]` raises `KeyError` on missing values (fail fast).

## Scaffold

The skeleton lives in `Deck/skel/` as an Ansible role with auto-discovery:

```text
skel/
├── Taskfile.yaml            # task python -- '{...}'
├── ansible.cfg
├── inventory/local.yml
├── playbooks/python.yaml    # thin: skel_type + role
└── roles/skel/
    ├── defaults/
    │   ├── main.yml         # common: author
    │   └── python.yml       # python_version, app_name
    ├── tasks/main.yml       # generic: discover → render
    └── templates/python/    # drop .j2 files here
```

Conventions: `dot_` prefix → dotfiles, `pkg/` → `app_name/`.
Adding a template = dropping a `.j2` file in the right place.

## See also

- [coding_guidelines](coding_guidelines.md)
