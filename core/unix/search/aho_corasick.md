---
title: Aho-Corasick
tags:
  - unix
  - algorithms
  - search
  - grep
aliases:
  - Aho-Corasick
  - Dictionary Matching
description: Multi-pattern fixed-string search with tries, failure links, and output sets.
---

# Aho-Corasick

Aho-Corasick searches for **many fixed strings at once**. It combines their
prefixes in a trie, then adds fallback transitions so the input can be scanned
in one pass without restarting from every byte for every pattern.

This is the algorithmic idea behind an important GNU grep fast path:

```bash
grep -F -e 'connection refused' -e 'timed out' app.log
grep -Ff known_errors.txt app.log
```

The command supplies a dictionary of literals. A mature tool may change its
exact implementation, but GNU grep documents Aho-Corasick as its preferred
approach for multiple fixed patterns when feasible.

## Why Not Search Each Pattern Separately?

Suppose the dictionary contains `he`, `hers`, `his`, and `she`. Four separate
searches reread the text and repeatedly compare the shared prefixes. A trie
stores each shared prefix once:

```text
root
|-- h -- e -- r -- s
|    `-- i -- s
`-- s -- h -- e
```

The trie alone is insufficient. When `sh` is followed by `e`, the matcher must
report both `she` and its suffix `he`. On a mismatch, it must also reuse the
longest suffix already read instead of returning unconditionally to the root.

## Three Parts of the Automaton

Each state represents a dictionary prefix and contains three kinds of data:

| Part | Purpose |
| ---- | ------- |
| Trie transition | Consume a byte that extends the current prefix |
| Failure link | Fall back to the longest proper suffix that is also a prefix |
| Output set | Report every pattern ending at this state |

Failure links are the multi-pattern analogue of preserving useful partial
progress. They are constructed breadth-first so the fallback state for a
shorter prefix is ready before a deeper state needs it.

```text
queue every child of root
while queue is not empty:
    state = queue.pop_front()
    for byte, child in state.transitions:
        fallback = state.failure
        while fallback is not root and byte is unavailable:
            fallback = fallback.failure
        child.failure = transition(fallback, byte) or root
        child.output += child.failure.output
        queue.push_back(child)
```

Copying or referencing the fallback output is essential. It is what lets the
`she` state also emit `he`.

## Search Walkthrough

With patterns `he`, `she`, `his`, and `hers`, scan the text `ushers`:

| Input byte | State after transition | Output |
| ---------- | ---------------------- | ------ |
| `u` | root | none |
| `s` | `s` | none |
| `h` | `sh` | none |
| `e` | `she` | `she`, `he` |
| `r` | `her` | none |
| `s` | `hers` | `hers` |

The transition from `she` on `r` follows failure links until the suffix `he`
can extend to `her`. The scanner never moves backward in the input.

A compact search loop is:

```python
state = root
for position, byte in enumerate(text):
    while state is not root and byte not in state.next:
        state = state.failure
    state = state.next.get(byte, root)
    for pattern in state.output:
        emit(pattern, position - len(pattern) + 1)
```

Overlapping matches are natural. For patterns `a` and `aa`, the input `aaa`
produces three `a` matches and two `aa` matches.

## Complexity

Let \(L\) be the sum of all pattern lengths, \(n\) the input length, and \(z\)
the number of reported matches.

| Phase | Cost |
| ----- | ---- |
| Insert patterns into a sparse trie | \(O(L)\) expected with hash maps |
| Build completed transitions | \(O(L \cdot alphabet)\) |
| Search | \(O(n + z)\) amortized |
| Sparse automaton memory | \(O(L)\) plus outputs |

A dense completed transition table makes every state transition constant-time.
For a fixed byte alphabet, its construction is linear in \(L\) with a large
constant, but it requires \(O(L \cdot alphabet)\) space and initialization.
Sparse maps store only real trie edges; their construction and lookup bounds
then depend on the map and failure-transition implementation. They save memory
for large alphabets at the cost of less predictable lookups and cache behavior.

The \(z\) term cannot be removed: an input that matches millions of patterns
requires at least enough work to report or count those matches.

## Engineering Tradeoffs

| Workload | Consequence |
| -------- | ----------- |
| One short pattern | Automaton construction is usually needless overhead |
| Stable dictionary, many inputs | Build cost is amortized well |
| Dictionary changes often | Rebuilding may dominate the search |
| Many shared prefixes | Trie saves substantial duplicated state |
| Huge dictionary | Memory use and cache locality become limiting factors |
| Dense matches | Output handling can dominate transition cost |

An implementation must also choose what its alphabet means. Byte-oriented
matching keeps transitions compact and matches how many Unix tools scan UTF-8
input. Code-point or locale-aware matching changes normalization, case folding,
character classes, and the size of the transition alphabet.

## Relation to grep and ripgrep

GNU grep documents a division of work: Boyer-Moore for one fixed pattern and
Aho-Corasick for several fixed patterns when those paths are available. The
observable contract is still `grep -F`; the chosen matcher is an implementation
detail.

Ripgrep also supports multiple `-F -e` patterns and pattern files, but should
not be described as permanently bound to one algorithm. Its Rust regex stack
can combine literal extraction, specialized multi-pattern search, and regex
verification according to the query. Aho-Corasick is one possible
[literal prefilter](literal_prefilters.md); Teddy is another for suitable
short literal sets.

For command examples, see [grep and ripgrep recipes](hacks/bash/grep.md). For
the surrounding traversal, I/O, and output work, see
[grep and ripgrep Internals](grep_and_ripgrep.md).

## See Also

- [Search](search.md) — section index
- [Boyer-Moore](boyer_moore.md) — one-pattern skip-based search
- [Two-Way String Matching](two_way.md) — one-pattern linear-time search
- [Literal Prefilters](literal_prefilters.md) — matcher selection and Teddy
- [Regex Automata](regex_automata.md) — automata for regular expressions
- [grep and ripgrep recipes](hacks/bash/grep.md) — multi-pattern commands

## References

- [Efficient String Matching: An Aid to Bibliographic Search](https://doi.org/10.1145/360825.360855)
- [GNU grep: Performance](https://www.gnu.org/software/grep/manual/html_node/Performance.html)
- [ripgrep](https://github.com/BurntSushi/ripgrep)
