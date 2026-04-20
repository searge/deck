---
tags:
  - bash
  - linux
  - snippets
title: Bash
aliases:
  - Bash
description: Bash one-liners for disk, locale, and package management.

---
# bash

General-purpose shell hacks. System config, package management, daily ops.

## Disk usage

```bash
du -h -d 1 | sort -hr
```

## Timezone / Locale / Hostname

```bash
dpkg-reconfigure tzdata
dpkg-reconfigure locales
```

```bash
hostnamectl set-hostname name
```

```bash
sudo hostnamectl set-hostname "Your Pretty HostName" --pretty
sudo hostnamectl set-hostname host.example.com --static
sudo hostnamectl set-hostname host.example.com --transient
```

## Install NVM

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
nvm install --lts || echo "$(nvm current) is already installed"
```

## List installed PHP modules (Debian/Ubuntu)

```bash
php_ver='8.3'
apt list --installed 2>/dev/null |
  grep "php${php_ver}-" | cut -d'/' -f1
```

## See also

- [parallel](parallel.md)
- [ssh](ssh.md)
- [find](find.md)
- [rsync](rsync.md)
- [user](user.md)
- [emacs_mode](emacs_mode.md)
