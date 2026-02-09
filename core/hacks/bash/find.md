---
tags:
  - bash
  - linux
  - filesystem
title: find
aliases:
  - find
description: find command patterns for file search and audit.

---

# find

## Wrong permissions

Find all directories with 777 and list them:

```bash
find -type d -perm 777 -exec bash -c 'ls -ld {}' \;
```

## Wrong user

Find files not belonging to a user:

```bash
find . ! -user $User -exec ls -lh {} \;
```

Count them:

```bash
find . ! -user $User | wc -l
```

## Find all git repositories

Discover repos and show remotes:

```bash
find . -type d -name .git \
  -exec bash -c "echo '{}' && cd '{}'/.. && git remote -v" \;
```
