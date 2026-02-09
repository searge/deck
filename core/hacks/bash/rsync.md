---
tags:
  - bash
  - deployment

---

# rsync

## With SSH config

```bash
rsync -e 'ssh -F ssh.cfg' -azhP \
  $host:$source $destination
```

## In CI/CD pipeline

```bash
rsync -az --quiet \
  --temp-dir=/tmp --partial-dir=/tmp --delete-after \
  --exclude-from=./.ignore . build_dist/$DEPLOY_VERSION
```
