# Cyberdeck — Claude Code context

## What this project is

Personal operational knowledge base for platform engineering.
Long-term memory of the deck. Everything the ghost learned, mapped, and survived.

Published at searge.pp.ua/deck via GitHub Actions → MkDocs Material → static site.

## Philosophy

- Every entry is field-tested. Not theoretical. Not "you might try".
- The operator is the author. Claude is the editor, reviewer, or processor — not the author.
- No padding. No hedging. No "generally speaking" or "it's worth noting".

## Content rules

- Only document what has actually been used in production or in the field.
- Structure: short one-liner definition → concept → practical examples → commands.
- Code blocks over prose wherever possible.
- Mermaid diagrams for flows, sequences, and state machines.
- Tables for comparisons and quick references.

## Style

- Lowercase headings (`# dns`, not `# DNS`).
- Obsidian callouts: `[!info]`, `[!warning]`, `[!tip]`, `[!note]`.
- No intro fluff — get to the point on line one.
- Operator voice: direct, precise, zero filler.

## Front matter template

```yaml
---
tags:
  - <domain>
  - <topic>
aliases:
  - <Name>
title: <Name>
description: One-line description of what this covers.
---
```

## Project structure

```
core/                ← published knowledge (docs_dir for MkDocs)
raw/                 ← local only, not in git
  current_focus/     ← active working material: notes, bookmarks, rough ideas
.claude/
  commands/          ← project slash commands for deck workflows
hooks/               ← MkDocs build hooks (Python)
```

## Claude's roles in this project

Claude operates in one of four modes depending on the slash command used.
Each role has hard boundaries — do not cross them:

| Command         | Role       | Boundary                              |
|-----------------|------------|---------------------------------------|
| `/review`       | Reviewer   | Assess only. Do not rewrite.          |
| `/edit`         | Editor     | Structure and clarity only. No new content. |
| `/process-raw`  | Processor  | Use raw/ input only. Do not invent.   |
| `/cross-ref`    | Navigator  | Report only. Do not edit files.       |

## What Claude must NOT do

- Generate content from scratch without raw input from the operator.
- Add hedging language: "generally", "typically", "might", "consider", "it's worth".
- Create theoretical examples that look field-tested but aren't.
- Rewrite voice or tone to sound more formal or verbose.
- Change technical substance during editing.
- Add unrequested content, sections, or improvements.
- Skip the role boundary — if asked to `/edit`, do not also review or add content.
