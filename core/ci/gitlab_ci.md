---
tags:
  - ci
  - cicd
  - gitlab
aliases:
  - GitLab CI
  - GitLab Pipelines
title: GitLab CI
description: GitLab CI pipeline patterns — pipeline anatomy, job naming, YAML anchors, scripts isolation, and environment promotion.
---

# GitLab CI

GitLab CI reads `.gitlab-ci.yml` from the repository root and runs the pipeline
on every push, merge request, or scheduled trigger. The pipeline definition is
YAML — which means the same discipline that applies to Ansible or Kubernetes
manifests applies here: structure first, then content.

## Pipeline anatomy

Every `.gitlab-ci.yml` follows the same top-to-bottom order:

```text
stages      → pipeline phases, in execution order
default     → runner tags, image, and settings that apply to every job
variables   → pipeline-wide environment variables
.anchors    → YAML anchors (hidden jobs starting with `.`)
jobs        → actual jobs, grouped by stage
tests       → linters, code quality — at the end
```

This order is a reading contract. `stages` tells you what the pipeline does.
`default` tells you where it runs. `variables` tells you what it knows.
Everything else follows.

```yaml
stages:
  - build
  - deploy

default:
  tags: [docker]
  image: golang:1.22

variables:
  GIT_DEPTH: 1
  GIT_STRATEGY: clone
```

## Stages and execution order

Stages define the sequence. All jobs within a stage run in parallel; the next
stage starts only when all jobs in the previous one finish.

```yaml
stages:
  - lint
  - build
  - deploy
```

This default behavior can be overridden with `needs`, which turns the pipeline
into a DAG — jobs run as soon as their declared dependencies finish, regardless
of stage:

```yaml
deploy:prod:
  stage: deploy
  needs: ["build:package"]   # runs as soon as build:package is done
```

`dependencies` is the older alternative to `needs`. It only controls which
artifacts are downloaded, not execution order. Prefer `needs` — it does both.

## Variables

Variables follow a hierarchy. Each level overrides the one above:

```text
GitLab CI/CD settings (UI)   → project/group/instance level, can be masked
.gitlab-ci.yml variables:    → pipeline-wide defaults
job-level variables:         → override for a specific job
```

Pipeline-wide variables set in the file are the default fallback:

```yaml
variables:
  DEPLOY_TIMEOUT: "300"
  ARTIFACT_DIR: build/dist
```

A job can override any of these:

```yaml
deploy:prod:
  variables:
    DEPLOY_TIMEOUT: "600"   # production needs more time
```

Sensitive values (SSH keys, API tokens, passwords) belong in GitLab's
**CI/CD Settings → Variables**, not in the YAML file. Variables stored there
can be masked (hidden in logs), protected (only on protected branches), and
scoped to a specific environment so they are only injected when that
environment is active.

## Job naming

One convention: `<purpose>:<location>` — lowercase, colon separator.

```yaml
build:app:          # compile the application
build:package:      # create a deployable artifact
deploy:dev:         # deploy to development
deploy:stage:       # deploy to staging
deploy:prod:        # deploy to production
check:health:prod:  # health check after production deploy
```

The colon creates a readable hierarchy. A flat list of `deploy_stage`,
`deploy_prod`, `deploy_prod_old` is harder to scan than the colon form.
Deeper chains are fine when they reflect real structure: `deploy:bucket:prod`
clearly means "deploy to the S3 bucket in production".

> [!info] Convention
> This is a personal naming preference, not a GitLab requirement. GitLab itself
> has no naming rules for jobs. Other teams use `deploy-prod`, `Deploy to Prod`,
> or plain `deploy`. The colon form is compact, scannable, and sorts well in the
> UI.

## YAML anchors

YAML anchors are the primary reuse mechanism in `.gitlab-ci.yml`. There are
two patterns: script snippets and job templates.

### Script snippets

A hidden key (starting with `.`) holds a sequence of script steps. Jobs
include it with `*name`:

```yaml
.ssh_agent: &ssh_agent
  - |
    eval $(ssh-agent -s)
    echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -

deploy:prod:
  before_script:
    - *ssh_agent
    - source ./scripts/ci/remote.sh
```

### Job templates

A hidden job holds a full or partial job definition. Other jobs merge it
with `<<: *name` and only override what differs:

```yaml
.prepare: &prepare
  stage: lint
  image: registry.example.com/ansible:latest
  allow_failure: false
  before_script:
    - ansible-lint --version
    - yamllint --version

ansible-lint:
  <<: *prepare
  script:
    - lint_ansible $CHANGED_FILES

yamllint:
  <<: *prepare
  script:
    - lint_yaml $CHANGED_FILES
```

`<<:` copies all keys from the anchor. Keys defined in the job override the
merged values. Use templates when jobs share most of their configuration and
differ only in `script:`.

### Organizing anchors

For small pipelines, define anchors at the top of `.gitlab-ci.yml` before the
first real job.

For larger pipelines, keep anchors in a separate file inside `.gitlab/`:

```text
.gitlab/
└── ci/
    ├── anchors.yml     # shared YAML anchors
    └── templates.yml   # shared job templates
```

Include them at the top of `.gitlab-ci.yml`:

```yaml
include:
  - local: .gitlab/ci/anchors.yml
  - local: .gitlab/ci/templates.yml
```

Common anchor names and when they appear:

| Anchor | Provides |
|--------|----------|
| `&ssh_agent` | SSH key injection |
| `&prepare` | Stage + image + version checks |
| `&deploy` | Full deploy job template |
| `&common_vars` | Computed variables (versions, dates, colors) |
| `&pull_changes` | Git fetch + reset + pull sequence |

## Scripts isolation

Long or complex shell logic does not belong inline. Move it to `scripts/ci/`:

```text
scripts/
└── ci/
    ├── remote.sh          # SSH helper: defines run_remote()
    ├── deploy.sh          # deploy logic
    ├── lint_changed.sh    # lint_ansible() and lint_yaml() functions
    ├── build.sh           # build steps
    └── check_health.sh    # post-deploy health verification
```

Jobs source helper files and call their functions:

```yaml
deploy:prod:
  before_script:
    - *ssh_agent
    - source ./scripts/ci/remote.sh
  script:
    - run_remote ./scripts/ci/deploy.sh ${CI_COMMIT_SHORT_SHA}
```

`remote.sh` defines `run_remote()` — a wrapper around `ssh` with consistent
options. The deploy logic runs on the target host. The CI job only orchestrates.

Benefits:

- CI jobs stay readable — one line calls one script
- Scripts are testable locally without a runner
- Debugging is simple: run the script directly with the same arguments

## Environments and variables

GitLab's `environment` keyword does two things: it tracks deployments in the
GitLab UI (under Deployments → Environments), and it activates environment-scoped
CI/CD variables. Variables stored in GitLab for a specific environment are only
injected into jobs that declare that environment.

```yaml
.deploy_package: &deploy_package
  stage: deploy
  before_script:
    - *ssh_agent
    - source ./scripts/ci/remote.sh
  script:
    - ./scripts/ci/deploy.sh $DEPLOY_ENV

deploy:stage:
  <<: *deploy_package
  environment:
    name: staging
  variables:
    DEPLOY_ENV: staging
  only:
    refs:
      - /^release-.*$/

deploy:prod:
  <<: *deploy_package
  environment:
    name: production
  variables:
    DEPLOY_ENV: production
  only:
    refs:
      - /^release-.*$/
```

Both jobs use the same `*deploy_package` template. The only differences are
the environment name and `DEPLOY_ENV`. Environment-specific secrets (SSH keys,
API credentials) are stored in GitLab scoped to `staging` or `production` and
never appear in the YAML.

This keeps the file small. A multi-environment pipeline is many jobs of five
lines each, not many copies of the same fifty lines.

## Include

For pipeline components shared across multiple repositories, use `include` with
a dedicated templates project:

```yaml
include:
  - project: "org/ci-templates"
    ref: main
    file: "/sonar.yml"
  - project: "org/ci-templates"
    ref: main
    file: "/review.yml"
```

The `org/ci-templates` project holds canonical job definitions. Projects include
them at a pinned ref. The included files typically define hidden job templates;
each consuming project merges and overrides only what it needs.

Use `include` when the same job appears in three or more repositories. Two
repositories sharing a job definition is cheaper as duplication than as a
managed shared dependency.

## Rules vs only/except

`only/except` is the legacy syntax. `rules` is the modern replacement and
handles conditions that `only/except` cannot express.

For simple branch-based triggers, `only` is still readable and concise:

```yaml
deploy:prod:
  only:
    - main
```

For conditions involving pipeline source, merge request data, or variables,
`rules` is more precise:

```yaml
# Legacy — two separate conditions, unclear AND/OR semantics
build:
  only:
    refs:
      - merge_requests
    variables:
      - $CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "main"

# Modern — one explicit expression
build:
  rules:
    - if: >-
        $CI_PIPELINE_SOURCE == "merge_request_event" &&
        $CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "main"
```

Long conditions use `>-` (folded scalar — newlines become spaces):

```yaml
update:config:
  rules:
    - if: >-
        $CI_PIPELINE_SOURCE == "merge_request_event" &&
        $CI_MERGE_REQUEST_SOURCE_BRANCH_NAME =~ /^release-.*$/ &&
        $CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "stage"
      when: manual
```

`rules` evaluates top-to-bottom and stops at the first match. A job with no
matching rule is excluded from the pipeline entirely.

Do not mix `rules` and `only/except` in the same job — GitLab treats them as
mutually exclusive and `rules` wins.

## Runners

Runners execute jobs. GitLab offers three scopes:

| Scope | Shared with |
|-------|-------------|
| Instance | All projects on the GitLab instance |
| Group | All projects in a group |
| Project | One specific project |

Each runner has an **executor** that determines how jobs run:

| Executor | Isolation | Typical use |
|----------|-----------|-------------|
| `shell` | None (runs as runner user) | Deploy jobs, direct host access |
| `docker` | Container per job | Build, test, lint |
| `kubernetes` | Pod per job | Cloud-native, autoscaling |

Tags route jobs to the right runner. A job with no tags runs on any untagged
runner:

```yaml
default:
  tags: [docker]         # all jobs use a Docker runner by default

deploy:prod:
  tags: [shell, prod]    # this job needs direct host access
```

Runner tags are arbitrary strings configured on the runner and matched in the
job. Common conventions: executor type (`docker`, `shell`), OS (`ubuntu`,
`alpine`), environment (`prod`, `staging`), or capability (`k8s`, `gpu`).

The `default:` block sets tags for all jobs. Override at the job level only
when a specific job needs a different executor or environment.

## Pipeline control

### DAG with needs

`needs` turns the pipeline into a directed acyclic graph. A job starts as soon
as all its `needs` are satisfied, without waiting for the rest of its stage:

```yaml
deploy:stage:
  stage: deploy
  needs: ["build:package"]

deploy:stage:rollback:
  stage: deploy
  needs: ["deploy:stage"]
  when: on_failure        # runs only if deploy:stage failed
```

`deploy:stage` does not wait for other build jobs to finish — only its own
artifact. `deploy:stage:rollback` runs only on failure and cleans up.

### Manual gates

```yaml
deploy:prod:
  when: manual
  needs:
    - job: deploy:stage
      artifacts: false    # stage succeeded, but no files needed
```

`when: manual` pauses the pipeline and waits for a human click in the GitLab
UI. Use it for production deployments and anything irreversible.

### Artifacts

```yaml
artifacts:
  when: on_success
  paths:
    - build/dist/*.tar.gz
  expire_in: 4h
```

`expire_in` prevents artifact accumulation. Downstream jobs declared in `needs`
download artifacts automatically. Set `artifacts: false` in `needs` when only
the job status matters, not its files.

## Script style

Multi-line scripts use `|` (literal block scalar):

```yaml
script:
  - |
    # Install kompose
    curl -L "${KOMPOSE_URL}/${KOMPOSE_VERSION}/${KOMPOSE_EXE}" -o kompose
    chmod +x kompose
    mv ./kompose /usr/local/bin/kompose
```

The comment on the first line acts as a label in the GitLab job log. Keep it
short and factual: `# Install kompose`, `# Set git credentials`, `# AGENT:`.

Long single commands use `>-` (folded stripped — newlines become spaces):

```yaml
script:
  - >-
    sonar-scanner
    -Dsonar.qualitygate.wait=true
    -Dsonar.gitlab.project_id=$CI_PROJECT_ID
    -Dsonar.gitlab.commit_sha=$CI_COMMIT_SHA
```

Use `|` for sequences of commands. Use `>-` for one command with many flags.

## What to avoid

| Don't | Do instead |
|-------|------------|
| Long shell logic inline | Move to `scripts/ci/` |
| Secrets in `variables:` | GitLab CI/CD Settings → Variables |
| `only/except` for complex conditions | `rules:` |
| Mixing `rules` and `only` in one job | Pick one |
| One stage for everything | Model the actual flow: lint → build → deploy |
| Missing `expire_in` on artifacts | Set short expiry (1h–4h for build artifacts) |
| `needs` pointing at stage peers | `needs` is for cross-stage DAG edges |
| Copy-pasting job definitions | YAML anchors + `<<:` merge |

## References

- [GitLab CI/CD reference](https://docs.gitlab.com/ee/ci/yaml/)
- [GitLab environments](https://docs.gitlab.com/ee/ci/environments/)
- [GitLab CI/CD variables](https://docs.gitlab.com/ee/ci/variables/)
- [YAML optimization](https://docs.gitlab.com/ee/ci/yaml/yaml_optimization.html)
- [Pipeline efficiency](https://docs.gitlab.com/ee/ci/pipelines/pipeline_efficiency.html)
- [Runners](https://docs.gitlab.com/ee/ci/runners/)
