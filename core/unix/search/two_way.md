---
title: Two-Way String Matching
tags:
  - unix
  - algorithms
  - search
  - performance
aliases:
  - Two-Way
  - Two-Way Search
description: Linear-time constant-space substring search using critical factorization and periods.
---

# Two-Way String Matching

The Two-Way algorithm searches for one fixed substring in linear worst-case
time using constant auxiliary space. It preprocesses the **periodic structure**
of the needle, splits it at a critical position, and uses both halves to choose
safe shifts through the haystack.

It complements Boyer-Moore:

- Boyer-Moore uses character and suffix tables to make large practical skips;
- Two-Way uses factorization and periods to guarantee linear progress without
  an alphabet-sized table.

Modern substring libraries can combine Two-Way with a SIMD prefilter, so most
positions are rejected cheaply while Two-Way supplies the robust fallback.

## Periods

A positive integer \(p\) is a period of a string when characters \(p\) places
apart agree wherever both positions exist.

```text
string:  abcabcabc
period:  3
         abc|abc|abc
```

Highly periodic needles are difficult for naive skipping rules because the
same partial match appears at many nearby alignments. Two-Way detects this
structure during preprocessing and remembers which comparisons can be reused.

## Critical Factorization

Split a needle \(P\) into two parts:

$$
P = P_{left}P_{right}
$$

A critical factorization chooses the split so the local period visible around
the boundary equals the period that matters for the complete needle. The
critical factorization theorem guarantees such a position exists.

```text
needle:  [ left part | right part ]
                       ^ critical position
```

The preprocessing algorithm finds maximal suffixes under two opposite
lexicographic orders. The better candidate yields the critical position and a
candidate period. This takes \(O(m)\) time for a needle of length \(m\) and
stores only a few indices.

The ordering is an implementation device, not a locale-sensitive comparison
of user text. A byte search orders byte values while computing the split.

## Search Phase

At each alignment, Two-Way performs two directional checks:

1. compare the right part from left to right;
2. if it matches, compare the left part from right to left;
3. report a match if both halves match;
4. otherwise shift by an amount proved safe by the mismatch and period.

```text
haystack:  .............candidate alignment........
needle:            [ left | right ]
                             -----> first
                       <-----       second
```

A mismatch in the right part identifies a prefix of that part that cannot
match at the following alignments, so the needle moves past them. A mismatch in
the left part permits a period-based shift because the right part is already
known to match.

### Periodic Needles

When the needle is periodic, shifting by its period creates comparisons that
overlap the previous alignment. Two-Way keeps a small memory index recording
the prefix already implied by the last successful right-half comparison. It
does not compare that region again.

### Non-Periodic Needles

When the proposed period does not describe the whole needle, the algorithm can
use a larger shift derived from the two part lengths. No periodic memory is
needed because the relevant overlap cannot repeat indefinitely.

These two cases are why a complete implementation is more intricate than the
high-level two-direction description.

## Complexity

| Property | Cost |
| -------- | ---- |
| Needle preprocessing | \(O(m)\) |
| Haystack search | \(O(n)\) worst case |
| Auxiliary memory | \(O(1)\) |
| Input movement | Forward only |

The proof charges comparisons to forward progress: critical factorization,
period shifts, and the periodic memory rule prevent the same unresolved work
from accumulating across alignments.

Linear worst-case time does not mean every byte is compared exactly once, nor
does it guarantee that Two-Way beats a vectorized or native implementation on
a particular corpus.

## Comparison with Other Literal Searchers

| Algorithm | Main advantage | Main limitation |
| --------- | -------------- | --------------- |
| Naive | No preprocessing | Quadratic worst case |
| Rabin-Karp | Tiny setup; convenient rolling hash | Hash candidates need verification |
| Boyer-Moore | Large skips on favorable text | Tables and difficult periodic inputs |
| Two-Way | Linear worst case and constant space | More complex preprocessing |
| SIMD filter | Rejects many positions per instruction | Needs a verifier and hardware paths |

These choices are composable. A SIMD filter can find candidate positions and
Two-Way can take over when candidates become too frequent.

## Use in Modern Literal Search

The Rust `memchr` crate documents a workload-sensitive substring strategy:

- Rabin-Karp for very small haystacks, minimizing setup latency;
- a generic SIMD search for short needles;
- Two-Way for the remaining cases;
- an optional SIMD candidate prefilter whose effectiveness is monitored.

This is relevant to the Rust regex stack used by ripgrep, but it does not mean
every `rg -F` invocation executes Two-Way. The regex and literal layers select
among multiple algorithms, and their heuristics are implementation details.

For GNU grep, the documented single-fixed-pattern fast path is Boyer-Moore.
Both tools therefore demonstrate the same broader lesson: the command contract
does not prescribe the substring algorithm.

## When to Implement It

Use a mature `find`, `memmem`, or regex API for application code. Implement
Two-Way when studying linear string matching, building a portable low-memory
search primitive, or validating a specialized runtime where worst-case bounds
matter.

Tests should emphasize:

- empty and one-byte needles;
- needle longer than the haystack;
- repeated and highly periodic bytes;
- matches at both boundaries;
- absent needles with long partial matches;
- every possible short input over a small alphabet.

Exhaustive short-input tests and fuzzing are especially valuable because an
incorrect shift can silently skip a valid match.

## See Also

- [Search](search.md) — section index
- [Boyer-Moore](boyer_moore.md) — skip tables for one fixed pattern
- [Literal Prefilters](literal_prefilters.md) — SIMD and matcher dispatch
- [Aho-Corasick](aho_corasick.md) — multiple fixed patterns
- [grep and ripgrep Internals](grep_and_ripgrep.md) — tool-level selection

## References

- [Two-way string-matching](https://doi.org/10.1016/0020-0190(91)90038-D)
- [Crochemore and Perrin string matching](https://www-igm.univ-mlv.fr/~lecroq/string/node26.html)
- [memchr algorithms](https://docs.rs/crate/memchr/latest/source/README.md)
- [ripgrep](https://github.com/BurntSushi/ripgrep)
