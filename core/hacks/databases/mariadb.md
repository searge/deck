---
tags:
  - databases
  - mariadb
aliases:
  - MariaDB
title: MariaDB
description: MariaDB connection, dump, and restore commands.
---

# mariadb

## Environment

```bash
MYSQL_HOST=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=
```

## Connect

```bash
mariadb --ssl-verify-server-cert=false \
  -h ${MYSQL_HOST} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE}
```

## Dump

```bash
mariadb-dump --ssl-verify-server-cert=false \
  -h ${MYSQL_HOST} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} > \
  /mnt/nfs/backup.$(date +%F).sql;
```
