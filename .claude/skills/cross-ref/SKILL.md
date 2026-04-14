---
name: cross-ref
description: Audit cross-references for a deck page — find missing inbound and outbound links. Report only, no edits.
user-invocable: true
---

Audit cross-references for the deck page at $ARGUMENTS.

Read the target file. Then search core/ for related pages.

Report:

1. **Missing outbound links** — concepts or tools mentioned in this page that have dedicated pages in core/ but aren't linked. Format: `term → core/path/to/page.md`

2. **Missing inbound links** — pages in core/ that are closely related and should link to this page but don't. Format: `core/path/to/page.md → suggested anchor text`

3. **Suggested "see also" section** — if 2 or more items found, provide a ready-to-paste markdown block.

Do not edit any files. Report only.
