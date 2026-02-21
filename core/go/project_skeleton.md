---
tags:
  - go
  - architecture
  - template
aliases:
  - Go Project Skeleton
title: Project Skeleton
description: Standard Go project layout for functional CLI tools — cmd/internal/pkg, go.mod, Taskfile, and skel.
---

# Project Skeleton

A minimal starting point for Go CLI tools. Scaffold new projects with:

```bash
cd ~/Documents/Deck/skel/
task go -- '{"project_name":"my-tool","description":"What it does","target_dir":"~/Code/lrn/my-tool"}'
```

## Directory layout

```text
project-name/
├── cmd/
│   ├── root.go              # cobra root, Execute()
│   ├── version.go           # version command
│   └── hello.go             # example command (delete or rename)
├── internal/
│   └── config/
│       ├── config.go        # FromEnv(), Default() — pure functions
│       └── config_test.go   # table-driven tests
├── pkg/
│   └── display/
│       ├── display.go       # Lipgloss styles, pure render functions
│       └── display_test.go
├── docs/
│   └── coding_guidelines.md
├── main.go                  # cmd.Execute() only
├── go.mod
├── Taskfile.yaml
├── .golangci.yaml
├── .gitignore
└── README.md
```

`internal/` packages cannot be imported by external modules.
`pkg/` packages are safe to import from other modules.

### When to add layers

**Small tool** — keep flat: `cmd/` + `internal/config/` + `pkg/display/`.

**Growing CLI** — add domain logic:

```text
internal/
├── config/
└── service/        # business logic (pure functions)
```

**Backend service** — add HTTP layer:

```text
internal/
├── config/
├── handler/        # HTTP: validate input → call service → write response
├── service/        # business logic, no HTTP knowledge
└── store/          # data access: interface + implementation
api/                # OpenAPI specs or protobuf definitions
```

## go.mod

```go
module github.com/Searge/project-name

go 1.24

require (
    github.com/charmbracelet/lipgloss v1.1.0
    github.com/spf13/cobra v1.10.0
)
```

Run `go mod tidy` after creation to populate indirect dependencies.

## Taskfile.yaml

```bash
task setup      # go mod tidy + download
task fmt        # go fmt ./...
task lint       # go vet + golangci-lint
task test       # go test -v ./...
task build      # build to bin/
task dev        # fmt + lint + test + build
task run        # go run . [args after --]
```

## main.go

```go
package main

import "github.com/Searge/project-name/cmd"

func main() {
    cmd.Execute()
}
```

Five lines. All logic lives in `cmd/`, `internal/`, or `pkg/`.

## cmd/root.go pattern

```go
var rootCmd = &cobra.Command{
    Use:   "app",
    Short: "Short description",
    Run: func(cmd *cobra.Command, _ []string) {
        _ = cmd.Help()
    },
}

func Execute() {
    if err := rootCmd.Execute(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}
```

Use `RunE` (returns `error`) for commands with logic — Cobra handles error printing.

## Scaffold

Templates live in `Deck/skel/roles/skel/templates/go/`. Adding a file =
dropping a `.j2` template in the right subdirectory.

```text
skel/
├── Taskfile.yaml               # task go -- '{...}'
├── playbooks/go.yaml           # thin: skel_type + role
└── roles/skel/
    ├── defaults/
    │   └── go.yml              # go_version, go_module, binary_name
    ├── tasks/main.yml          # generic: discover → render
    └── templates/go/           # .j2 files mirror project structure
```

Conventions: `dot_` prefix → dotfiles (e.g. `dot_gitignore.j2` → `.gitignore`).

## See also

- [coding_guidelines](coding_guidelines.md)
