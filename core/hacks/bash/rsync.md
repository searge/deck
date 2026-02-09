---
tags:
  - bash
  - deployment
title: rsync
aliases:
  - rsync
description: rsync recipes for deployment and backup.

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

## Mirror directory (delete removed files)

```bash
rsync -avz --delete $source/ $destination/
```

## Dry run (preview changes)

```bash
rsync -avzn --delete $source/ $destination/
```

## Bandwidth limit

```bash
rsync -avz --bwlimit=5000 $source $destination  # 5MB/s
```
