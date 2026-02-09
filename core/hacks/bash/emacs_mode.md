---
tags:
  - bash
  - shell
  - keybindings

---

# emacs_mode

Shell readline shortcuts (default bash keybindings).

## Movement

| Key | Action |
|-----|--------|
| `Ctrl-a` | Move to start of line |
| `Ctrl-e` | Move to end of line |
| `Ctrl-b` | Back one character |
| `Alt-b` | Back one word |
| `Ctrl-f` | Forward one character |
| `Alt-f` | Forward one word |
| `Ctrl-] x` | Forward to next occurrence of x |
| `Alt-Ctrl-] x` | Back to previous occurrence of x |

## Deletion

| Key | Action |
|-----|--------|
| `Ctrl-u` | Delete to beginning of line |
| `Ctrl-k` | Delete to end of line |
| `Ctrl-w` | Delete to start of word |
| `Ctrl-y` | Paste from kill ring |

## Case

| Key | Action |
|-----|--------|
| `Alt-c` | Capitalize to end of word |
| `Alt-u` | Uppercase to end of word |
| `Alt-l` | Lowercase to end of word |

## Undo

| Key | Action |
|-----|--------|
| `Ctrl-x Ctrl-u` | Undo last change |
| `Alt-r` | Undo all changes to line |
| `Ctrl-l` | Clear screen |

## History

| Key / Sequence | Action |
|----------------|--------|
| `Ctrl-r` | Incremental reverse search |
| `Alt-p` | Non-incremental reverse search |
| `!!` | Execute last command |
| `!abc` | Last command starting with abc |
| `!$` | Last argument of last command |
| `!^` | First argument of last command |
| `^abc^xyz` | Replace abc with xyz in last command |
