---
title: grep and ripgrep Internals
tags:
  - unix
  - grep
  - ripgrep
  - performance
  - internals
aliases:
  - grep Internals
  - ripgrep Internals
description: How grep and ripgrep select matchers, traverse files, scan input, and produce output.
---

# grep and ripgrep Internals

`grep` and `rg` do not run one universal search algorithm. They are pipelines
that adapt to the pattern, input, requested output, and available fast paths.

```mermaid
flowchart LR
    Q[Query] --> P[Parse pattern]
    P --> L[Extract literals]
    L --> M[Select matcher]
    M --> I[Choose input strategy]
    I --> S[Scan bytes]
    S --> B[Find line boundaries]
    B --> O[Format output]
```

Optimizing only the matcher can be irrelevant when directory traversal, page
faults, Unicode handling, line counting, or terminal output dominates the run.

## Query Shape Selects the Work

| Query shape | Example | Available optimization |
| ----------- | ------- | ---------------------- |
| One fixed literal | `grep -F error` | [Boyer-Moore](boyer_moore.md) or [vectorized/linear search](two_way.md) |
| Several literals | `grep -F -e error -e warning` | [Aho-Corasick-style multi-pattern automaton](aho_corasick.md) |
| Regex with a required literal | `rg 'error: [0-9]+'` | [Literal prefilter](literal_prefilters.md) before regex verification |
| Regex without a required literal | `rg '[a-z]{30}'` | Regex engine must do most of the work |
| Look-around or backreference | `rg -P '(?<=id=)[0-9]+'` | PCRE2 backtracking engine |

A literal prefilter finds candidate positions cheaply. The full regex engine
then verifies only those candidates. For some patterns, the prefilter can do
nearly all of the search; for others, no useful literal exists.

The prefilter itself is selected by workload. It may use byte search, a
single-substring algorithm, Teddy SIMD fingerprints, or Aho-Corasick. See
[Literal Prefilters](literal_prefilters.md) for the dispatch and verification
contract.

## GNU grep

POSIX specifies observable `grep` behavior, not its internal matcher. GNU grep
combines several implementations and may change the selection between releases.

| Pattern | GNU grep path when feasible |
| ------- | --------------------------- |
| One fixed pattern | Boyer-Moore family |
| Multiple fixed patterns | Aho-Corasick |
| Basic or extended regex | [DFA-based fast matcher](regex_automata.md) |
| Backreferences and unusual features | Slower verification matcher |

`grep -F` states that the pattern is fixed text. Even without `-F`, a regex may
contain a mandatory literal that can be used as a prefilter.

### Locale

GNU grep is generally faster in a single-byte locale because it can avoid
multi-byte character processing:

```bash
LC_ALL=C grep -F -- 'literal' large-file.txt
```

This is valid only when byte-oriented semantics are acceptable. Locale affects
character classes, case folding, collation, and what counts as valid text; it is
not a transparent performance flag for every query.

## ripgrep

Ripgrep was designed for recursive code search, so it performs substantial work
before matching file content.

| Layer | Responsibility |
| ----- | -------------- |
| Traversal | [Walk directories in parallel](parallel_traversal.md) |
| Filtering | Apply `.gitignore`, `.ignore`, `.rgignore`, hidden, and binary rules |
| Pattern engine | Use finite-automata-based regex matching by default |
| Prefilter | Extract literals and use optimized, often SIMD-assisted searches |
| Input | Choose memory maps or incremental buffered reads |
| Records | Enforce line-oriented matching unless multiline mode is enabled |
| Output | Count lines, add paths, colors, context, or structured JSON |

`rg -F` disables regex syntax, but it should not be described as
"Boyer-Moore in Rust." Ripgrep and its regex libraries can choose among several
literal strategies. Those details change as the implementation evolves.

### Default Engine vs PCRE2

The default regex engine uses finite automata and excludes features such as
look-around and backreferences. This keeps worst-case matching time bounded.
PCRE2 is available when those features are necessary:

```bash
# Default engine
rg 'service-[0-9]+' .

# PCRE2 for look-behind
rg -P '(?<=service-)[0-9]+' .
```

PCRE2 is not automatically slower for every query, but it changes the engine,
available optimizations, and worst-case behavior.

### Traversal and Filtering

By default, ripgrep skips ignored, hidden, and binary files. GNU grep recursive
search and ripgrep therefore do not search the same corpus without additional
flags.

```bash
# Show why ripgrep ignored a path
rg --debug 'needle' .

# Disable ignore, hidden, and binary filtering for a controlled text corpus
rg -uuu -F -- 'needle' ./corpus
```

`--debug` is primarily useful for traversal and ignore decisions. It is not a
stable "show me the selected matcher" interface.

Ripgrep distributes directory work using work stealing. Each worker consumes
local paths and can steal a batch from another worker when it becomes idle.
Ignore matching and subtree pruning occur as part of this traversal; see
[Parallel Search Traversal](parallel_traversal.md).

## Input Strategy

Searching one large file and searching thousands of small files stress
different parts of the system:

| Corpus | Likely dominant cost |
| ------ | -------------------- |
| One cached large file | Matcher and memory bandwidth |
| One cold large file | Storage and page faults |
| Many small files | Traversal, metadata, open/close calls |
| Dense matches | Line discovery and output |
| Compressed files | Decompression or preprocessing |

Ripgrep can choose between memory mapping and buffered reads. Mapping can help a
small number of large files, while creating mappings for many small files may
cost more than buffered scanning.

## Output Is Part of the Benchmark

These commands do different amounts of work:

```bash
rg -q -F 'error' .        # stop after proving that a match exists
rg -l -F 'error' .        # print every matching path
rg -n -F 'error' .        # find lines, count them, print every matching line
rg -C 3 -F 'error' .      # also collect and render context
```

High match counts often make output processing more expensive than detection.
Sending output to `/dev/null` removes terminal rendering, but the tool still
finds line boundaries and formats the bytes it writes.

## Fair Tool Comparison

For a controlled directory containing only text files:

```bash
pattern='QUORUM_RECOVERY_SEQUENCE_42'
corpus='./corpus'

# Align fixed-string semantics and suppress output rendering
time LC_ALL=C grep -rF -- "$pattern" "$corpus" >/dev/null
time rg --no-config -uuu -F -- "$pattern" "$corpus" >/dev/null
```

Record the versions and run more than once:

```bash
grep --version | head -n 1
rg --version | head -n 1

# Separate syscall and CPU effects when investigating a difference
strace -c grep -rF -- "$pattern" "$corpus" >/dev/null
perf stat rg --no-config -uuu -F -- "$pattern" "$corpus" >/dev/null
```

Even this is not a universal ranking. Change the number and size of files,
pattern shape, match density, cache state, locale, or requested output and the
result may reverse.

## Practical Choice

| Situation | Prefer |
| --------- | ------ |
| POSIX script or stdin pipeline | `grep` |
| Recursive source-tree search | `rg` |
| Fixed text | `-F` with either tool |
| Complex Perl-compatible regex | `rg -P` or `grep -P` when supported |
| Need exact portability | POSIX grep syntax, not GNU-only flags |
| Performance investigation | Controlled corpus and equivalent semantics |

## See Also

- [Search](search.md) — section index
- [Boyer-Moore](boyer_moore.md) — algorithm and reproducible benchmark
- [Two-Way String Matching](two_way.md) — linear-time single-literal search
- [Aho-Corasick](aho_corasick.md) — matching several fixed strings in one pass
- [Literal Prefilters](literal_prefilters.md) — SIMD candidates and regex
  verification
- [Regex Automata](regex_automata.md) — Thompson NFA, DFA variants, and
  backtracking
- [Parallel Search Traversal](parallel_traversal.md) — work stealing and ignore
  matching
- [grep and ripgrep recipes](hacks/bash/grep.md) — daily command reference

## References

- [GNU grep: Performance](https://www.gnu.org/software/grep/manual/html_node/Performance.html)
- [GNU grep manual](https://www.gnu.org/software/grep/manual/grep.html)
- [ripgrep](https://github.com/BurntSushi/ripgrep)
- [ripgrep User Guide](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)
- [ripgrep FAQ](https://github.com/BurntSushi/ripgrep/blob/master/FAQ.md)
