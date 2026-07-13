---
tags:
  - go
  - architecture
aliases:
  - Go Coding Guidelines
title: Coding Guidelines
description: Standards for Go CLI and service projects — functional core, errors as values, small interfaces.
---

# Coding Guidelines — Go

Standards for Go CLI and service projects. Applies functional principles
within Go idioms: errors as values, small interfaces, pure core logic.

## Core principles

1. **Functional core** -- pure functions for business logic, side effects at edges
2. **Immutable data** -- return new values, do not mutate inputs
3. **Explicit errors** -- errors as values, always wrapped with context
4. **Small interfaces** -- defined at point of use, one or two methods
5. **No global state** -- pass configuration and dependencies explicitly

## Project structure

### What goes where

| Directory | Purpose |
| --------- | ------- |
| `cmd/` | Cobra commands — thin wrappers only, no logic |
| `internal/` | App-private packages, not importable externally |
| `pkg/` | Reusable packages safe to import from other modules |
| `main.go` | `cmd.Execute()` only, 5-10 lines |

Optional for backend projects:

| Directory | Purpose |
| --------- | ------- |
| `internal/handler/` | HTTP handlers — validate input, call service, write response |
| `internal/service/` | Business logic — pure functions, no HTTP knowledge |
| `internal/store/` | Data access — interface + implementation |
| `api/` | OpenAPI specs or protobuf definitions |

### Dependency direction

```text
cmd      -> internal/config, pkg/display
handler  -> service
service  -> store (interface)
store    -> database/external API
pkg      -> standard library only (keep portable)
```

## Functions

### Pure functions

The core of functional style: same input always produces same output,
no side effects.

```go
// Pure: deterministic, no I/O, no mutation
func filterByStatus(tickets []Ticket, status Status) []Ticket {
    result := make([]Ticket, 0, len(tickets))
    for _, t := range tickets {
        if t.Status == status {
            result = append(result, t)
        }
    }
    return result
}
```

### Composition via function types

Use function types and closures to compose behavior.

```go
type Predicate func(Ticket) bool

func withStatus(s Status) Predicate {
    return func(t Ticket) bool { return t.Status == s }
}

func withPriority(p Priority) Predicate {
    return func(t Ticket) bool { return t.Priority == p }
}

func filter(tickets []Ticket, predicates ...Predicate) []Ticket {
    result := make([]Ticket, 0, len(tickets))
    for _, t := range tickets {
        if all(t, predicates) {
            result = append(result, t)
        }
    }
    return result
}

// Usage
active := filter(tickets, withStatus(Active), withPriority(High))
```

### Impure shell

Push I/O (API calls, DB, files) to the outer layer. Keep inner functions pure.

```go
// Impure shell: fetches data, delegates logic to pure functions
func (s *Service) SummaryReport(ctx context.Context) (Report, error) {
    tickets, err := s.store.All(ctx)   // side effect: I/O
    if err != nil {
        return Report{}, fmt.Errorf("fetch tickets: %w", err)
    }
    return buildReport(tickets), nil   // pure
}

// Pure core: no I/O, easy to test
func buildReport(tickets []Ticket) Report {
    return Report{
        Total:  len(tickets),
        ByPrio: groupByPriority(tickets),
    }
}
```

## Error handling

Errors are values. Always wrap with context. Never ignore.

```go
// Wrap with %w to preserve the chain
if err != nil {
    return fmt.Errorf("load config: %w", err)
}

// Sentinel errors for callers to check
var ErrNotFound = errors.New("not found")

// Early return to keep nesting flat
func process(id int) (Result, error) {
    if id <= 0 {
        return Result{}, fmt.Errorf("invalid id %d", id)
    }
    item, err := fetch(id)
    if err != nil {
        return Result{}, fmt.Errorf("fetch %d: %w", id, err)
    }
    return transform(item), nil
}
```

## Interfaces

Define interfaces where they are **consumed**, not where they are implemented.
Keep them small -- one or two methods.

```go
// Defined in the service package (consumer), not in store package
type TicketStore interface {
    All(ctx context.Context) ([]Ticket, error)
    ByID(ctx context.Context, id int) (Ticket, error)
}

// Accept interfaces, return concrete types
func NewService(store TicketStore) *Service {
    return &Service{store: store}
}
```

## Data modeling

Structs are the primary data type. Use constructors for validation.
Do not export fields that should not be mutated externally.

```go
// Config is immutable after construction
type Config struct {
    LogLevel string
    Debug    bool
}

// Constructor validates and returns a value (not pointer for small structs)
func NewConfig(logLevel string, debug bool) (Config, error) {
    if err := validateLogLevel(logLevel); err != nil {
        return Config{}, fmt.Errorf("config: %w", err)
    }
    return Config{LogLevel: logLevel, Debug: debug}, nil
}

// Document enum values with their source
type Status int

const (
    StatusNew      Status = 1 // Source: GLPI Ticket.php
    StatusAssigned Status = 2
    StatusSolved   Status = 5
)
```

## Concurrency

Pass `context.Context` as the first parameter to every function that
does I/O or may need cancellation.

```go
func (c *Client) Fetch(ctx context.Context, id int) (Ticket, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return Ticket{}, fmt.Errorf("build request: %w", err)
    }
    // ...
}
```

For goroutines, always provide a way to signal completion.

```go
func process(ctx context.Context, items []Item) error {
    g, ctx := errgroup.WithContext(ctx)
    for _, item := range items {
        item := item // capture loop variable (Go < 1.22)
        g.Go(func() error {
            return handle(ctx, item)
        })
    }
    return g.Wait()
}
```

## CLI patterns

### Command structure (Cobra)

One file per command. Commands are thin: parse flags, validate, call logic.

```go
var serveCmd = &cobra.Command{
    Use:   "serve",
    Short: "Start HTTP server",
    RunE: func(cmd *cobra.Command, _ []string) error {
        cfg, err := config.FromEnv()
        if err != nil {
            return fmt.Errorf("load config: %w", err)
        }
        return server.Start(cmd.Context(), cfg)
    },
}
```

Use `RunE` (returns error) instead of `Run` — lets Cobra handle error printing.

### Output (Lipgloss)

Define semantic styles once in `pkg/display`, use everywhere.

```go
// pkg/display/display.go
var (
    StyleHeader  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("6"))
    StyleSuccess = lipgloss.NewStyle().Foreground(lipgloss.Color("2")).Bold(true)
    StyleError   = lipgloss.NewStyle().Foreground(lipgloss.Color("1")).Bold(true)
    StyleDim     = lipgloss.NewStyle().Foreground(lipgloss.Color("8"))
)

func Header(title string) string {
    line := strings.Repeat("─", 64)
    return StyleHeader.Render(line) + "\n  " + title + "\n" + StyleHeader.Render(line)
}
```

### Optional: HTTP handler pattern

```go
// Handler validates and delegates — no business logic here
func (h *Handler) GetTicket(w http.ResponseWriter, r *http.Request) {
    id, err := strconv.Atoi(chi.URLParam(r, "id"))
    if err != nil {
        writeError(w, http.StatusBadRequest, "invalid id")
        return
    }
    ticket, err := h.service.GetByID(r.Context(), id)
    if errors.Is(err, service.ErrNotFound) {
        writeError(w, http.StatusNotFound, "ticket not found")
        return
    }
    if err != nil {
        writeError(w, http.StatusInternalServerError, "internal error")
        return
    }
    writeJSON(w, http.StatusOK, ticket)
}
```

## Testing

Table-driven tests are the Go standard. Use `_test` package suffix
for black-box tests.

```go
func TestFilterByStatus(t *testing.T) {
    tickets := []Ticket{
        {ID: 1, Status: StatusNew},
        {ID: 2, Status: StatusSolved},
        {ID: 3, Status: StatusNew},
    }

    tests := []struct {
        name   string
        status Status
        want   int
    }{
        {"new tickets", StatusNew, 2},
        {"solved tickets", StatusSolved, 1},
        {"missing status", StatusAssigned, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := filterByStatus(tickets, tt.status)
            if len(got) != tt.want {
                t.Errorf("got %d tickets, want %d", len(got), tt.want)
            }
        })
    }
}
```

## Tooling

```bash
task setup      # go mod tidy + download
task fmt        # go fmt ./...
task lint       # go vet + golangci-lint
task test       # go test -v ./...
task build      # build binary to bin/
task dev        # fmt + lint + test + build
```

Individual checks:

```bash
go vet ./...
golangci-lint run
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
```

## Naming

| Element | Convention | Example |
| ------- | ---------- | ------- |
| Packages | lowercase, singular | `display`, `config`, `ticket` |
| Exported types | PascalCase | `TicketStatus`, `Config` |
| Interfaces | noun or `-er` suffix | `Store`, `Fetcher` |
| Constructors | `New*` or `From*` | `NewClient`, `FromEnv` |
| Errors | `Err*` prefix | `ErrNotFound` |
| Short locals | OK in small scope | `i`, `v`, `t`, `ok` |

## What to avoid

| Don't | Do instead |
| ----- | ---------- |
| `panic` in library code | return `error` |
| Global mutable state | pass dependencies as parameters |
| Ignored errors (`_`) | handle or explicitly document why |
| Large interfaces (>3 methods) | split into smaller interfaces |
| Pointer to small struct | pass by value |
| `interface{}` / `any` everywhere | concrete types or generics |
| Business logic in `cmd/` | move to `internal/service/` or `pkg/` |
| Missing context parameter | always first for I/O functions |

## References

- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Standard Go Project Layout](https://github.com/golang-standards/project-layout)
- [charmbracelet/lipgloss](https://github.com/charmbracelet/lipgloss)
- [spf13/cobra](https://github.com/spf13/cobra)
- [Python Guidelines](py/coding_guidelines.md) -- same principles, Python context
- [Project Skeleton](project_skeleton.md) -- directory layout and scaffold
