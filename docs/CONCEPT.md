# CONCEPT

This is a cyberdeck recovered from an abandoned netrunner's den in Night City, circa 2077. Its core contains a structured knowledge base — part personal wiki, part navigational system — built around container orchestration, platform engineering, and the deeper layers of UNIX philosophy.

The deck follows POSIX modularity: each module is self-contained, does one thing, and connects to others through clean interfaces. The `core/` is the ghost's long-term memory — everything the netrunner learned, mapped, and survived. Around it, `daemons/` run autonomously, `docs/` describe the system itself, and `templates/` provide reusable blueprints. Nothing is decorative. Every directory exists because the ghost needs it to navigate.

The structure is designed to grow without rotting. New modules slot into `core/` the same way you'd install a new daemon or mount a new drive — the system doesn't care how many there are, as long as each one knows its boundaries. When in doubt, the rule is the same one that built UNIX: keep it small, keep it sharp, make it composable.

## Structure

```bash
Deck/
├── assets/
├── templates/
├── daemons/                  # Automation, scripts
│
├── docs/                     # The system describes itself
│   ├── CONCEPT.md            # This file. Why the deck exists
│   └── SCHEMA.md             # Conventions: naming, tagging, linking
│
└── core/                     # Long-term memory
    ├── net/                  # Networking, DNS, mesh, protocols
    ├── hacks/                # Snippets, runbooks, quick access
    └── .../                  # Modular expansion
```

## Principles

- **Everything is a node.** Each page is self-contained and linkable, like a UNIX file
- **Flat over deep.** Maximum 3 levels of nesting. If you need more, split the module
- **Name things once.** A daemon is a daemon in UNIX, in Cyberpunk, and in this deck
- **The ghost navigates.** Structure serves recall, not taxonomy
