---
tags:
  - drupal
  - snippets
aliases:
  - Drush
title: Drush
description: Drush CLI for Drupal — database operations, cache, config, and site management.
---

# drush

## Database

### Dump

```bash
# Drush dump with gzip
drush sql:dump --gzip --result-file=/tmp/dump-$(date +%F).sql
```

```bash
# Direct mysqldump
mysqldump $DB_NAME | gzip > /tmp/dump-$(date +%F).sql.gz
```

### Import

```bash
# Decompress and import
gzip -d /tmp/dump-$(date +%F).sql.gz
drush sql:cli < /tmp/dump-$(date +%F).sql
```

```sql
-- Or via mysql directly
SOURCE /tmp/dump-2024-01-01.sql;
```

### Database size

```sql
SELECT table_schema "DB Name",
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) "DB Size in MB"
FROM information_schema.tables
GROUP BY table_schema;
```

## Cache

```bash
# Clear all caches
drush cr

# Rebuild (clear + rebuild routes, containers)
drush cache:rebuild
```

## Configuration

Export config:

```bash
drush config:export
```

Import config:

```bash
drush config:import
```

Show diff before import:

```bash
drush config:status
```

## Site maintenance

```bash
# Maintenance mode on/off
drush state:set system.maintenance_mode 1
drush state:set system.maintenance_mode 0

# Run database updates
drush updatedb

# Check status
drush status

# One-time login link
drush uli
```

## User management

```bash
# Create user
drush user:create $USERNAME --mail="user@example.com" --password="$PASS"

# Block/unblock
drush user:block $USERNAME
drush user:unblock $USERNAME

# Reset password
drush user:password $USERNAME "$NEWPASS"

# Add role
drush user:role:add administrator $USERNAME
```

## Watchdog (logs)

```bash
# Show recent logs
drush watchdog:show

# Show errors only
drush watchdog:show --severity=error

# Tail logs
drush watchdog:tail
```
