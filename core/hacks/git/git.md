---
tags:
  - git
  - snippets
title: Git
aliases:
  - Git
description: Git workflow, stash, rebase, and common operations.

---

# git

## Config

```bash
git config --global color.ui true
git config --global core.pager 'less -r'
git config --global pull.rebase true
git config --global init.defaultBranch main
```

## Stash

```bash
git stash                                  # save staged + unstaged
git stash -u                               # include untracked
git stash save "wip: feature X"            # with message
git stash show                             # summary
git stash show -p                          # full diff
git stash list                             # all stashes
git stash pop                              # apply + remove
git stash pop stash@{2}                    # specific stash
git stash drop stash@{0}                   # remove without applying
```

## Branches

```bash
git branch -a                              # list all branches
git branch -d feature/old                  # delete merged branch
git branch -D feature/old                  # force delete
git checkout -b feature/new                # create and switch
git switch -c feature/new                  # same, modern syntax
```

## Rebase

```bash
git rebase main                            # rebase current onto main
git rebase --abort                         # cancel mid-rebase
git rebase --continue                      # after resolving conflicts
```

## Log

```bash
git log --oneline --graph --all            # visual history
git log --oneline -10                      # last 10 commits
git log --author="name" --since="2 weeks"  # filtered
git log -p -- path/to/file                 # file history with diff
```

## Undo

```bash
git reset HEAD~1                           # undo last commit (keep changes)
git reset --hard HEAD~1                    # undo last commit (discard changes)
git checkout -- file.txt                   # discard changes in file
git restore file.txt                       # same, modern syntax
```

## Cleanup

```bash
git clean -fd                              # remove untracked files + dirs
git clean -fdn                             # dry run
git remote prune origin                    # remove stale remote refs
```

## Tags

```bash
git tag v1.0.0                             # lightweight tag
git tag -a v1.0.0 -m "Release 1.0.0"      # annotated tag
git push origin v1.0.0                     # push single tag
git push origin --tags                     # push all tags
```

## See also

- [git_cicd](git_cicd.md)

## References

- [A Visual Git Reference](https://marklodato.github.io/visual-git-guide/index-en.html)
