---
tags:
  - git
  - cicd
  - gitlab
title: Git CI/CD
aliases:
  - Git CI/CD
description: GitLab CI/CD pipeline snippets for git operations.

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

## Configure git in pipeline

```yaml
.git_config: &git_config
  - git config --global user.email "ci@example.com"
  - git config --global user.name "CI Bot"
  - git remote set-url origin "https://oauth2:${CI_TOKEN}@gitlab.com/${CI_PROJECT_PATH}.git"
```

## Shallow clone (faster CI)

```yaml
variables:
  GIT_DEPTH: 1
  GIT_STRATEGY: fetch
```
