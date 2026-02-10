---
tags:
  - search
  - snippets
aliases:
  - Solr
title: Solr
description: Apache Solr administration — health checks, core management, backup, and troubleshooting.
---

# solr

## Service

```bash
systemctl status solr
systemctl restart solr
```

## Health and info

Check version:

```bash
curl -s http://localhost:8983/solr/admin/info/system?wt=json | jq '.lucene'
```

List cores:

```bash
curl -s http://localhost:8983/solr/admin/cores?wt=json | jq '.status'
```

Ping a core:

```bash
curl -s http://localhost:8983/solr/$CORE/admin/ping
```

## Data directory and backup

Find data directory:

```bash
curl -s http://localhost:8983/solr/admin/info/system?wt=json | jq -r '.solr_home'
```

Backup a core via API:

```bash
curl "http://localhost:8983/solr/$CORE/replication?command=backup&location=/tmp/solr-backup"
```

Backup data directory manually:

```bash
SOLR_HOME=$(curl -s http://localhost:8983/solr/admin/info/system?wt=json | jq -r '.solr_home')
rsync -azhP "$SOLR_HOME" ~/solr-backup/data
```

## Core management

Create a core:

```bash
solr create -c $CORE -d _default
```

Delete a core:

```bash
solr delete -c $CORE
```

Reload a core (after config changes):

```bash
curl "http://localhost:8983/solr/admin/cores?action=RELOAD&core=$CORE"
```

## Troubleshooting

### Not responding to remote connections

Solr binds to localhost by default. To listen on all interfaces, add to `/etc/default/solr.in.sh`:

```bash
SOLR_JETTY_HOST="0.0.0.0"
```

Then reload:

```bash
systemctl daemon-reload
systemctl restart solr
```

### Java home

Find Java path:

```bash
readlink -f /usr/bin/javac | sed "s:/bin/javac::"
```

Set it:

```bash
export JAVA_HOME='/usr/lib/jvm/java-11-openjdk-amd64'
export PATH=$JAVA_HOME/bin:$PATH
```

Or permanently in `/etc/default/solr.in.sh`:

```bash
SOLR_JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"
```

### Check logs

```bash
tail -f /var/solr/logs/solr.log
```

## Uninstall

```bash
service solr stop
rm -r /var/solr
rm -r /opt/solr
rm /etc/init.d/solr
rm /etc/default/solr.in.sh
deluser --remove-home solr
deluser --group solr
update-rc.d -f solr remove
```
