---
title: Search
tags:
  - unix
  - algorithms
  - performance
  - search
aliases:
  - Search Internals
description: Fixed strings, regular expressions, and the internals of Unix search tools.
---

# Search

Text search in Unix spans more than one algorithm. A user supplies a pattern,
but a tool still has to interpret it, select a matcher, read files, find line
boundaries, and render results.

This section separates three layers:

```text
recipe                 tool pipeline                 matcher
grep -F needle .  ->   traversal + I/O + output  ->  Boyer-Moore or another fast path
```

The exact matcher is an implementation decision. The command contract and the
operational result matter more than preserving one internal algorithm forever.

## Algorithms

- [Boyer-Moore](boyer_moore.md) — right-to-left fixed-string search with
  bad-character and good-suffix shifts
- [Two-Way String Matching](two_way.md) — linear-time constant-space search
  using critical factorization and periods
- [Aho-Corasick](aho_corasick.md) — trie and failure links for matching many
  fixed strings in one pass
- [Regex Automata](regex_automata.md) — Thompson NFA, full and lazy DFA, and
  the boundary with backtracking engines
- [Literal Prefilters](literal_prefilters.md) — literal extraction, SIMD
  candidate search, Teddy, and regex verification

## Tool Internals

- [grep and ripgrep](grep_and_ripgrep.md) — pattern analysis, matcher selection,
  file traversal, input strategies, and output costs
- [Parallel Search Traversal](parallel_traversal.md) — work stealing, ignore
  matching, filesystem scheduling, and scaling limits

## Commands

- [grep and ripgrep recipes](hacks/bash/grep.md) — daily searches, filtering,
  scripts, and exit codes

Future algorithm pages belong here when they explain a real path through Unix
search tools. The directory is not a general algorithm catalogue.
