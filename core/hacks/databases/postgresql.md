---
tags:
  - databases
  - postgresql
aliases:
  - PostgreSQL
title: PostgreSQL
---

# postgresql

## Dump and restore

```bash
# Dump into custom-format archive
pg_dump -U $user -Fc $database > /tmp/db-prod.dump

# Restore into existing database
pg_restore -d $database -c --if-exists -O -U $user /tmp/db-prod.dump
```

## Copy between Kubernetes clusters

```bash
# Export from source cluster
kubectl exec -n $ns $pod -- tar cf - /tmp/db.dump | tar xf - -C /tmp/

# Import to target cluster
kubectl cp -n $ns /tmp/tmp/db.dump $pod:/tmp/
```

## Interactive session

```bash
psql -U $user -d $database
```

## Drop and recreate

```sql
\c postgres;
DROP DATABASE mydb;
```
