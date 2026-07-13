---
title: Boyer-Moore
tags:
  - unix
  - algorithms
  - performance
  - grep
aliases:
  - Boyer-Moore
  - String Search
  - Text Search
description: >-
  Boyer-Moore heuristics, pathological inputs, and reproducible grep and
  ripgrep benchmarks.
---

# Boyer-Moore

Boyer-Moore searches for a fixed pattern by comparing from **right to left**.
A mismatch near the pattern's end can prove that several following alignments
are impossible, allowing the search to skip text it never inspects.

More text does not make a search take less time. Boyer-Moore can inspect a
smaller **fraction** of a larger text, and longer patterns often permit larger
skips. This distinction is often lost in short explanations of "sublinear"
search.

## Two Shift Rules

For pattern \(P\), text \(T\), current alignment \(s\), and a mismatch at
pattern position \(j\), Boyer-Moore takes the largest safe shift from two
precomputed tables.

### Bad Character

If the mismatching text byte does not occur in the pattern, the pattern can move
past it. If it does occur, align the text byte with its rightmost useful
occurrence in the pattern:

$$
shift_{bad} = j - last(T[s+j])
$$

For a byte alphabet, `last` is a fixed 256-entry table. Building it is
\(O(\lvert P\rvert + 256)\); lookup during search is \(O(1)\).

### Good Suffix

If a suffix already matched before the mismatch, move the pattern until:

1. another occurrence of that suffix aligns with the text; or
2. a prefix of the pattern aligns with the suffix; or
3. the pattern moves completely past the matched suffix.

The good-suffix rule is what distinguishes full Boyer-Moore from the simpler
Boyer-Moore-Horspool variant, which uses one bad-character-style table.

```text
pattern:       EXAMPLE
text:    HERE IS A SIMPLE EXAMPLE
                       ^ compare from here toward the left
```

## Complexity

| Property | Cost |
| -------- | ---- |
| Pattern preprocessing | \(O(\lvert P\rvert + \lvert alphabet\rvert)\) |
| Table memory | \(O(\lvert P\rvert + \lvert alphabet\rvert)\) |
| Typical search | Sublinear character inspections |
| Worst case in the lab implementation | \(O(\lvert T\rvert\lvert P\rvert)\) |
| Refined variants with the Galil rule | \(O(\lvert T\rvert + \lvert P\rvert)\) |

"Sublinear" describes inspected characters, not permission to ignore input I/O.
A CLI tool may still read or map the whole file while its matcher examines only
selected byte positions.

## When Skips Collapse

Boyer-Moore benefits from a long pattern and a varied alphabet. Repeated text
over a small alphabet produces short shifts because the mismatching byte and
matched suffix occur throughout the pattern.

The lab includes this adversarial pair:

```text
text:    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...aaaaab
pattern: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab
```

At almost every alignment, the final `b` mismatches an `a`. Because `a` occurs
immediately before `b` in the pattern, the bad-character rule can advance only
one byte. The good-suffix rule has no matched suffix to exploit.

## Benchmark Design

The implementation is in `scripts/unix/boyer_moore_benchmark.py`. It compares:

| Method | Scope |
| ------ | ----- |
| Naive Python | In-memory byte comparisons |
| Boyer-Moore Python | In-memory, both shift tables precompiled |
| `bytes.find` | Optimized CPython native implementation |
| `grep -F` | File scan plus process startup |
| `rg -F` | File scan plus process startup |

The benchmark deliberately does **not** put those numbers on equal footing.
Pure Python measures algorithmic work plus interpreter overhead. `bytes.find`
runs native code. `grep` and `rg` include subprocess startup and filesystem
access. Their first run warms the page cache; reported values are medians of
subsequent runs.

Two deterministic corpora expose both sides of the algorithm:

- **typical:** 2 MiB of varied ASCII, 27-byte pattern found only at EOF;
- **adversarial:** 128 KiB of repeated `a`, 32-byte pattern found only at EOF.

Putting the only match at EOF forces every method to search the full range.
Sending output to `/dev/null` prevents terminal rendering from dominating the
CLI measurements.

## Run the Lab

```bash
# Text report with in-memory and available CLI tools
uv run python scripts/unix/boyer_moore_benchmark.py

# Faster smoke test without subprocess measurements
uv run python scripts/unix/boyer_moore_benchmark.py \
  --size-mib 1 --repeats 2 --skip-cli

# Interactive throughput chart
uv run python scripts/unix/boyer_moore_benchmark.py \
  --html /tmp/boyer_moore.html
```

The report includes both wall time and operation counts. Comparison counts are
portable enough to explain the algorithm; throughput is specific to the CPU,
Python build, tool versions, corpus, page cache, and filesystem.

## Reading the Result

On the typical corpus, Boyer-Moore should use far fewer alignments and
comparisons than naive search. Its preprocessing cost is amortized when the same
pattern searches a large text or many texts.

On the adversarial corpus, both Python implementations perform nearly the same
number of alignments. This is the important failure mode hidden by a single
best-case benchmark.

For the default generated corpora, the typical alignment counts are `2,097,126`
for naive search and `77,673` for Boyer-Moore, a reduction of about 27 times. In
the adversarial case, both perform exactly `131,041` alignments. These counts are
deterministic; elapsed time is not.

`bytes.find` will usually beat a handwritten Python Boyer-Moore even when the
latter does less conceptual work. Algorithm choice, implementation language,
vectorization, memory access, and call overhead all contribute to observed
speed.

GNU grep documents Boyer-Moore as one matcher it may use for a single fixed
pattern, but explicitly treats that as an implementation detail. For the full
tool pipelines, see [grep and ripgrep Internals](grep_and_ripgrep.md).

## Choosing a Searcher

| Workload | Practical choice |
| -------- | ---------------- |
| One literal in Python bytes | `bytes.find`, not handwritten search |
| One fixed CLI pattern | `grep -F` or `rg -F` |
| Many fixed patterns | [Aho-Corasick](aho_corasick.md) family |
| Regex over a repository | `rg` with [automata](regex_automata.md) by default |
| Teaching skip heuristics | Boyer-Moore |

Implement Boyer-Moore to understand it or when building a specialized matcher.
For operational work, prefer the standard library and mature search tools, then
benchmark the exact corpus and query shape that matter.

## See Also

- [Search](search.md) — algorithms, tools, and the boundaries between them
- [Two-Way String Matching](two_way.md) — linear worst-case substring search
- [Aho-Corasick](aho_corasick.md) — multiple fixed patterns in one pass
- [Literal Prefilters](literal_prefilters.md) — SIMD candidate search and
  matcher dispatch
- [Regex Automata](regex_automata.md) — regular expressions as NFA and DFA
- [grep and ripgrep Internals](grep_and_ripgrep.md) — matcher selection, I/O,
  traversal, and output
- [grep and ripgrep recipes](hacks/bash/grep.md) — operational commands

## References

- [The Boyer-Moore Fast String Searching Algorithm](https://www.cs.utexas.edu/~moore/best-ideas/string-searching/)
- [A Fast String Searching Algorithm](https://www.cs.utexas.edu/~moore/publications/fstrpos.pdf)
- [GNU grep: Performance](https://www.gnu.org/software/grep/manual/html_node/Performance.html)
- [ripgrep](https://github.com/BurntSushi/ripgrep)
- [ripgrep User Guide](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)
