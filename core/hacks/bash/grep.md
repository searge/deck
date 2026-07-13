---
tags:
  - bash
  - linux
  - grep
  - ripgrep
aliases:
  - grep
  - rg
title: grep and ripgrep
description: Practical grep and ripgrep commands for files, repositories, scripts, and pipelines.
---

# grep and ripgrep

Use `grep` for portable scripts, stdin pipelines, and systems where it is
already available. Use `rg` for interactive recursive search over source trees.

## Fixed Text vs Regex

Use `-F` when the pattern is literal. It avoids accidental regex semantics and
gives the tool the clearest optimization opportunity.

```bash
# Literal string with line numbers
grep -Fn -- 'db.host[0]' config.ini
rg -Fn -- 'db.host[0]' .

# Extended regular expression
grep -En -- 'error|warning' app.log
rg -n -- 'error|warning' app.log
```

Always quote patterns. Use `--` before a user-controlled pattern so a leading
dash is not parsed as an option.

## Common Filters

```bash
# Case-insensitive, whole word
grep -inw -- 'timeout' app.log
rg -inw -- 'timeout' app.log

# Invert: lines that do not match
grep -vF -- 'healthcheck' access.log
rg -vF -- 'healthcheck' access.log

# Three lines of context on each side
grep -nC 3 -- 'panic' app.log
rg -nC 3 -- 'panic' app.log

# Print only the matching part
grep -Eo -- 'request_id=[a-f0-9]+' app.log
rg -o -- 'request_id=[a-f0-9]+' app.log
```

## Multiple Patterns

```bash
# Match either fixed string
grep -F -e 'connection refused' -e 'timed out' app.log
rg -F -e 'connection refused' -e 'timed out' app.log

# Load one pattern per line
grep -Ff patterns.txt app.log
rg -Ff patterns.txt app.log
```

Use `-F` with `-f` when `patterns.txt` contains literals rather than regular
expressions. The shared-prefix automaton behind this workload is explained in
[Aho-Corasick](unix/search/aho_corasick.md).

## Recursive Search

```bash
# GNU grep: recurse and restrict filenames
grep -rFn \
  --include='*.py' \
  --exclude-dir='.venv' \
  --exclude-dir='.git' \
  -- 'TODO' .

# ripgrep: recursive by default, respects ignore files
rg -Fn \
  -g '*.py' \
  -g '!.venv/**' \
  -- 'TODO' .
```

Ripgrep skips ignored, hidden, and binary files by default:

```bash
rg -u -- 'needle' .     # include ignored files
rg -uu -- 'needle' .    # also include hidden files
rg -uuu -- 'needle' .   # also search binary files
```

Use `rg --debug 'needle' .` to inspect why a path was ignored.

## Files, Counts, and Quiet Checks

```bash
# Paths containing at least one match
grep -rlF -- 'deprecated_api' .
rg -lF -- 'deprecated_api' .

# Count matching lines per file, not total occurrences
grep -rcF -- 'error' logs/
rg -cF -- 'error' logs/

# Stop after proving that any match exists
grep -qF -- 'READY' health.log
rg -qF -- 'READY' health.log
```

For a total count of occurrences rather than matching lines:

```bash
grep -oF -- 'error' app.log | wc -l
rg -oF -- 'error' app.log | wc -l
```

## Exit Codes in Scripts

Both tools use `0` for a match, `1` for no match, and `2` or another non-zero
status for an error. Do not collapse "not found" and "could not search."

```bash
if grep -qF -- "$needle" "$file"; then
    printf '%s\n' 'found'
else
    status=$?
    if (( status == 1 )); then
        printf '%s\n' 'not found'
    else
        printf 'grep failed with status %d\n' "$status" >&2
        exit "$status"
    fi
fi
```

Commands used as `if` conditions remain compatible with `set -e`.

## Machine-Readable Paths

Use NUL delimiters when paths may contain spaces or newlines:

```bash
rg -l0F -- 'legacy_function' . |
  xargs -0 -r -n 1 sed -n '1,20p' --
```

For structured match records:

```bash
rg --json -- 'request_id=[a-f0-9]+' logs/ | jq -c .
```

## Binary, Encoded, and Compressed Input

```bash
# Treat binary-looking input as text
grep -aF -- 'marker' image.bin
rg -aF -- 'marker' image.bin

# Search gzip input
zgrep -F -- 'error' app.log.gz
rg -zF -- 'error' logs/

# Explicit encoding in ripgrep
rg -E utf-16le -F -- 'service' windows.log
```

`rg -z` launches decompression helpers. Availability depends on installed
tools and supported compression formats.

## Fast Byte-Oriented grep

For ASCII literals where locale-aware semantics are unnecessary:

```bash
LC_ALL=C grep -rF -- 'literal' ./corpus
```

Do not apply this blindly to case-insensitive searches or locale-sensitive
character classes.

## See Also

- [bash](bash.md) — shell command collection
- [Search internals](unix/search/search.md) — algorithms and tool pipeline
- [grep and ripgrep Internals](unix/search/grep_and_ripgrep.md) — matcher
  selection, traversal, I/O, and output costs
- [Boyer-Moore](unix/search/boyer_moore.md) — fixed-string algorithm and
  benchmark
- [Aho-Corasick](unix/search/aho_corasick.md) — multiple fixed strings in one
  pass
- [Regex Automata](unix/search/regex_automata.md) — default regex execution and
  the boundary with PCRE2
- [Literal Prefilters](unix/search/literal_prefilters.md) — why required
  literals accelerate regexes
- [Parallel Search Traversal](unix/search/parallel_traversal.md) — work stealing
  and ignore-aware directory walking
