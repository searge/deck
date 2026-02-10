---
tags:
  - search
  - snippets
aliases:
  - Elasticsearch
title: Elasticsearch
description: Elasticsearch administration — cluster health, index management, queries, and troubleshooting.
---

# elasticsearch

## Cluster health

```bash
# Quick status (green/yellow/red)
curl -s localhost:9200/_cat/health

# Detailed health
curl -s localhost:9200/_cluster/health?pretty

# Per-shard health
curl -s localhost:9200/_cluster/health?level=shards&pretty
```

## Node info

```bash
# List nodes
curl -s localhost:9200/_cat/nodes?v

# Disk usage
curl -s localhost:9200/_cat/allocation?v

# Node stats
curl -s localhost:9200/_nodes/stats?pretty
```

## Index management

List indices:

```bash
curl -s localhost:9200/_cat/indices?v&s=index
```

Create an index:

```bash
curl -X PUT localhost:9200/$INDEX -H 'Content-Type: application/json' -d '{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1
  }
}'
```

Delete an index:

```bash
curl -X DELETE localhost:9200/$INDEX
```

Close/open (saves resources for unused indices):

```bash
curl -X POST localhost:9200/$INDEX/_close
curl -X POST localhost:9200/$INDEX/_open
```

## Documents

Index a document:

```bash
curl -X POST localhost:9200/$INDEX/_doc -H 'Content-Type: application/json' -d '{
  "title": "Test",
  "timestamp": "2024-01-01T00:00:00Z"
}'
```

Search:

```bash
curl -s localhost:9200/$INDEX/_search?pretty -H 'Content-Type: application/json' -d '{
  "query": { "match_all": {} },
  "size": 10
}'
```

Count documents:

```bash
curl -s localhost:9200/$INDEX/_count?pretty
```

## Snapshots and backup

Register a repository:

```bash
curl -X PUT localhost:9200/_snapshot/$REPO -H 'Content-Type: application/json' -d '{
  "type": "fs",
  "settings": { "location": "/mnt/backups/elasticsearch" }
}'
```

Create a snapshot:

```bash
curl -X PUT "localhost:9200/_snapshot/$REPO/snapshot_$(date +%F)?wait_for_completion=true"
```

List snapshots:

```bash
curl -s localhost:9200/_snapshot/$REPO/_all?pretty
```

Restore:

```bash
curl -X POST localhost:9200/_snapshot/$REPO/$SNAPSHOT/_restore
```

## Troubleshooting

### Red cluster

Check unassigned shards:

```bash
curl -s localhost:9200/_cat/shards?v | grep UNASSIGNED
```

Explain why a shard is unassigned:

```bash
curl -s localhost:9200/_cluster/allocation/explain?pretty
```

Force reroute (last resort):

```bash
curl -X POST localhost:9200/_cluster/reroute?retry_failed=true
```

### High disk usage

Check watermarks:

```bash
curl -s localhost:9200/_cluster/settings?include_defaults=true&pretty | grep watermark
```

Default thresholds: 85% (low), 90% (high), 95% (flood). Indices go read-only at flood.

Unblock read-only indices:

```bash
curl -X PUT localhost:9200/_all/_settings -H 'Content-Type: application/json' -d '{
  "index.blocks.read_only_allow_delete": null
}'
```

### Slow queries

Enable slow log:

```bash
curl -X PUT localhost:9200/$INDEX/_settings -H 'Content-Type: application/json' -d '{
  "index.search.slowlog.threshold.query.warn": "5s",
  "index.search.slowlog.threshold.query.info": "2s"
}'
```

Check hot threads:

```bash
curl -s localhost:9200/_nodes/hot_threads
```

### Service management

```bash
systemctl status elasticsearch
systemctl restart elasticsearch

# Check logs
journalctl -u elasticsearch -f
```
