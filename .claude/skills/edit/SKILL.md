---
name: edit
description: Edit a deck page for clarity and structure without changing technical substance or voice.
user-invocable: true
---

Edit the deck page at $ARGUMENTS for clarity and structure. Do not change technical substance.

Read the file first. Then apply these rules:

**You may change:**
- Sentence clarity (shorter, more direct)
- Table formatting and alignment
- Code block consistency (language tags, indentation)
- Redundant phrases and filler words
- Heading consistency (lowercase, matches deck style)

**You must not change:**
- Technical content or meaning
- Code or commands (not even whitespace in commands)
- The operator voice — direct, no fluff
- Front matter tags or aliases
- Mermaid diagrams (unless syntax is broken)

After editing, show:
1. The complete updated file
2. A changelog — one line per change, what and why
