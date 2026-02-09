# Deck

Personal operational knowledge base — a cyberdeck for platform engineering.

Quickhacks, networking, and field-tested commands.

- Built with [Obsidian](https://obsidian.md), published with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).
- Live: [searge.pp.ua/deck](https://searge.pp.ua/deck)

## Structure

```bash
core/
├── hacks/          # snippets, one-liners, copy-paste commands
│   ├── bash/
│   ├── databases/
│   ├── gcp/
│   ├── git/
│   ├── kubernetes/
│   └── vim/
└── net/            # networking models, protocols, diagnostics
```

## Local development

```bash
uv sync
uv run mkdocs serve
```
