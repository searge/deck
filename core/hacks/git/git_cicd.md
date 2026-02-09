---
tags:
  - git
  - cicd
  - gitlab

---

# git_cicd

Git operations inside CI/CD pipelines.

## Pull changes by tag

```yaml
.pull_changes_tag: &pull_changes
  - LAST_TAG="${CI_COMMIT_TAG}"
  - git fetch origin ${LAST_TAG}
  - git reset --hard ${CI_COMMIT_SHORT_SHA} && git checkout ${LAST_TAG}
  - git pull origin ${LAST_TAG} --rebase=true --allow-unrelated-histories
  - git remote -v; git status
```

## Pull changes by branch

```yaml
.pull_changes: &pull_changes
  - DEV_BRANCH="${CI_COMMIT_REF_NAME}"
  - SHORT_SHA="${CI_COMMIT_SHORT_SHA}"
  - git fetch origin $DEV_BRANCH
  - git reset --hard $SHORT_SHA && git checkout $DEV_BRANCH
  - git pull origin $DEV_BRANCH --rebase=true --allow-unrelated-histories
  - git remote -v; git status
```
