---
title: Literal Prefilters
tags:
  - unix
  - algorithms
  - search
  - regex
  - ripgrep
aliases:
  - Regex Prefilters
  - Literal Extraction
description: Literal extraction, candidate search, SIMD matchers, and regex verification.
---

# Literal Prefilters

A regex engine does not always need to run its automaton over every input byte.
If every match must contain a known literal, a faster matcher can first locate
candidate positions and invoke the full regex engine only where a match remains
possible.

```text
regex -> extract required literals -> select prefilter
                                         |
input -> fast candidate search --------->+-> regex verification -> match
```

This optimization is a major reason these two expressions can have very
different throughput:

```bash
rg 'error: [0-9]+' logs/  # required literal: "error: "
rg '[A-Za-z]{30}' logs/   # no useful required literal
```

## Soundness Contract

A prefilter may return a **false positive**: a position where its literal
occurs but the complete regex does not match. The regex engine rejects it
during verification.

A prefilter must not return a **false negative**. Skipping a real match changes
the result and is therefore incorrect.

| Result | Allowed? | Consequence |
| ------ | -------- | ----------- |
| Candidate is a real match | Yes | Regex confirms it |
| Candidate is not a real match | Yes | Extra verification work |
| Real match is not a candidate | No | Incorrect search result |

The optimization is profitable when candidates are rare. A common literal
such as `a` can create enough false positives that switching repeatedly between
the prefilter and regex engine costs more than scanning with the engine alone.

## Extracting Literals

The regex is first parsed into a syntax tree or high-level intermediate
representation. Static analysis then finds literals required by every path to
a match.

```text
(?:error|warning):
foo|[0-9]+
```

| Regex | Extractable information |
| ----- | ----------------------- |
| `error: [0-9]+` | Every match starts with `error:` followed by a space |
| `error` or `warning` before `:` | Every match starts with one of two literals |
| `[A-Z]+_TIMEOUT` | Every match contains `_TIMEOUT` |
| `foo(?:bar)?` | `foo` is required; `bar` is not |
| `foo` or `[0-9]+` | No literal is shared by every alternative |

Extraction may deliberately be conservative. Returning no prefilter loses an
optimization; incorrectly claiming that a literal is mandatory loses matches.

Literal sets also need simplification. If alternatives contain `sam`, `samwise`,
and `samwise gamgee`, finding `sam` is sufficient to produce every candidate.
Keeping all three may enlarge the matcher without eliminating more input.

## Matcher Dispatch

The best literal matcher depends on the number and lengths of the needles,
their prefixes, the input size, and the available CPU instructions. The Rust
`regex-automata` stack can select among strategies such as:

| Literal shape | Candidate strategy |
| ------------- | ------------------ |
| One useful byte | `memchr` or vectorized byte search |
| Two or three possible bytes | Multi-byte `memchr` variants |
| One longer literal | `memmem`, SIMD filtering, or Two-Way |
| Several short literals | Teddy SIMD prefilter |
| Larger literal set | Aho-Corasick |
| Small set of possible bytes | Byte-set search |

These are implementation choices, not guarantees attached to an `rg` flag.
Thresholds and heuristics can change between library releases.

## SIMD Candidate Search

A scalar scanner tests one input position at a time. SIMD instructions compare
many bytes in parallel, produce a bit mask of promising lanes, and verify only
the positions represented by set bits.

For one literal, a cheap filter can compare two discriminating bytes rather
than the whole needle at every position:

```text
needle:     configuration
selected:   c         t
input:   ...c.........t...  -> candidate; verify full needle
```

Selecting rare bytes normally produces fewer candidates than always selecting
the first and last bytes. If the filter proves ineffective on the observed
input, a searcher can stop paying its overhead and fall back to the underlying
linear-time algorithm.

SIMD improves the constant factor, not the asymptotic requirement to inspect
the input. It also requires scalar or narrower handling at buffer boundaries
and on CPUs without the selected instruction set.

## Teddy

Teddy is a multiple-literal SIMD prefilter originating in Intel Hyperscan. It
builds compact fingerprints from the initial bytes of several needles, checks
many input positions with packed operations, and returns a mask of candidates.

The fingerprints are intentionally cheaper than complete comparisons, so
collisions are acceptable. Each candidate is verified against the literals or
the full regex afterward.

Teddy and Aho-Corasick solve related but different jobs:

| Property | Teddy | Aho-Corasick |
| -------- | ----- | ------------- |
| Main mechanism | SIMD fingerprints | Trie and failure links |
| Result | Candidate locations | Exact dictionary matches |
| Best fit | Suitable small literal sets | General multi-pattern matching |
| False positives | Expected and verified | None for dictionary matching |
| Hardware dependence | Strong | Usually modest |

This makes Teddy useful as a prefilter without making it a replacement for
Aho-Corasick in every multi-pattern workload.

## Prefix, Suffix, and Inner Literals

A literal prefix gives the simplest pipeline: locate the prefix and run an
anchored forward regex search from that position. A required suffix can support
a reverse search for the match start.

An inner literal needs three stages:

```text
find inner literal -> reverse-search prefix -> forward-verify complete match
```

For `\w+(@!|%%)\w+`, the literals `@!` and `%%` are useful even though neither
starts the match. After finding one, a reverse automaton can locate a possible
start for the preceding `\w+`, then a normal forward search confirms the end.

Alternation complicates this optimization because each inner literal may
correspond to a different prefix. An engine should abandon the shortcut when it
cannot preserve that relationship safely.

## Construction vs Search

Prefilters introduce costs before and during matching:

- parse and analyze the regex;
- simplify the extracted literal set;
- construct the chosen matcher;
- switch between candidate search and regex verification;
- retain any matcher-specific tables or SIMD masks.

Construction is easy to amortize across a repository or a long stream. For a
tiny input, a low-setup algorithm such as Rabin-Karp may finish before a more
elaborate searcher has been built.

Benchmark both one-shot and reused searchers when evaluating a library API.
Command-line measurements also include process startup, traversal, file I/O,
line discovery, and output.

## Practical Consequences

Use a literal expression when that is the actual intent:

```bash
rg -F -- 'db.host[0]' .
grep -F -- 'db.host[0]' config.ini
```

For regexes, preserving a selective required literal can be faster than
rewriting the same condition into a broad character-class expression. Do not
change semantics only to influence a heuristic; matcher selection is an
implementation detail and may change.

`rg --debug` is useful for pattern, traversal, and ignore diagnostics, but its
output is not a stable API for proving which low-level prefilter was selected.

## See Also

- [Search](search.md) — section index
- [Two-Way](two_way.md) — linear-time single-literal fallback
- [Aho-Corasick](aho_corasick.md) — exact multi-pattern search
- [Regex Automata](regex_automata.md) — engines that verify candidates
- [grep and ripgrep Internals](grep_and_ripgrep.md) — complete tool pipeline

## References

- [regex-automata prefilter documentation](https://docs.rs/regex-automata/latest/regex_automata/util/prefilter/)
- [regex-automata reverse inner-literal optimization](https://docs.rs/regex-automata/latest/src/regex_automata/meta/reverse_inner.rs.html)
- [memchr algorithms](https://docs.rs/crate/memchr/latest/source/README.md)
- [ripgrep performance analysis](https://github.com/BurntSushi/blog/blob/master/content/post/ripgrep.md)
- [Hyperscan](https://github.com/intel/hyperscan)
