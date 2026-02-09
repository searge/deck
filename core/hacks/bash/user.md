---
tags:
  - bash
  - linux
  - administration
title: User management
aliases:
  - User management
description: Linux user and group administration commands.

---

# user

User and group management.

## Create user

```bash
useradd -m -s /usr/bin/zsh -c "Comment" -G adm,cdrom,sudo username
```

Batch create:

```bash
for user in alice bob charlie; do
  useradd -m -s /bin/bash -G sudo,adm "$user"
done
```

## Groups

List all groups:

```bash
cat /etc/group
```

Create group with specific GID:

```bash
groupadd -g 1008 mygroup
```

Assign primary group:

```bash
usermod -g primarygroup username
```

Assign secondary group (`-a` keeps existing groups):

```bash
usermod -a -G secondarygroup username
```

## Troubleshooting

```bash
usermod -u 1008 username
pkill -U 1005
pgrep -U username | xargs kill -9
ps -p 3822 -o comm=
```
