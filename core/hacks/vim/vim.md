---
tags:
  - vim
  - editor
title: Vim
aliases:
  - Vim
description: Vim survival kit — navigation, editing, and common operations.

---

# vim

## Modes

| Key | Mode | Description |
|-----|------|-------------|
| `i` | Insert | Type text before cursor |
| `a` | Insert | Type text after cursor |
| `o` | Insert | New line below |
| `Esc` | Normal | Command mode |
| `v` | Visual | Select characters |
| `V` | Visual Line | Select lines |
| `:` | Command | Ex commands |

## Navigation

| Key | Action |
|-----|--------|
| `h j k l` | Left, down, up, right |
| `w / b` | Next / previous word |
| `0 / $` | Start / end of line |
| `gg / G` | Start / end of file |
| `Ctrl-d / Ctrl-u` | Half page down / up |
| `/{pattern}` | Search forward |
| `?{pattern}` | Search backward |
| `n / N` | Next / previous match |

## Editing

| Key | Action |
|-----|--------|
| `dd` | Delete line |
| `yy` | Yank (copy) line |
| `p / P` | Paste after / before |
| `u` | Undo |
| `Ctrl-r` | Redo |
| `ciw` | Change inner word |
| `ci"` | Change inside quotes |
| `.` | Repeat last command |

## Paste mode

Disable autoindent before pasting:

```vim
:set paste
```

Re-enable after pasting:

```vim
:set nopaste
```

Toggle with F3 (add to `.vimrc`):

```vim
set pastetoggle=<F3>
```

## Search and replace

```vim
:%s/old/new/g       " replace all in file
:%s/old/new/gc      " replace with confirmation
:5,20s/old/new/g    " replace in line range
```

## File operations

```vim
:w                  " save
:q                  " quit
:wq                 " save and quit
:q!                 " quit without saving
:e filename         " open file
:split filename     " horizontal split
:vsplit filename    " vertical split
```

## References

- [Vim Cheat Sheet](https://vim.rtorr.com/lang/uk)
