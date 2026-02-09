---
tags:
  - git
  - snippets

---

# git

## Color config

```bash
git config --global color.ui true &&
git config --global core.pager 'less -r'
```

## Stash

Save uncommitted changes (staged and unstaged):

```bash
git stash
```

Include untracked files:

```bash
git stash -u
```

Annotate with a message:

```bash
git stash save "work in progress: feature X"
```

Show stash summary:

```bash
git stash show
```

Re-apply and remove from stash:

```bash
git stash pop
git stash pop stash@{2}  # specific stash
```

## Cleanup

Remove untracked files and directories:

```bash
git clean -fd
```

## See also

- [[git_cicd]]

## References

- [A Visual Git Reference](https://marklodato.github.io/visual-git-guide/index-en.html)
