---
title: Kubernetes Resource Triage
tags:
  - kubernetes
  - resources
  - troubleshooting
aliases:
  - Kubernetes OOM Triage
description: Read-only checks for scheduling capacity, throttling, OOM, quota, and eviction.
---

# Kubernetes Resource Triage

Separate scheduler accounting from live usage and kernel/kubelet enforcement.
The distinctions are explained in [Resources](k8s/resources.md).

## Effective Declarations

```bash
kubectl -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{.status.qosClass}{"\n"}{range .spec.containers[*]}{.name}{"\t"}{.resources}{"\n"}{end}'
kubectl -n "$NAMESPACE" get limitrange,resourcequota -o yaml
kubectl describe node "$NODE"
```

The Node description's allocated requests/limits are accounting summaries, not
current utilization.

## Current Metrics

```bash
kubectl top pod "$POD" -n "$NAMESPACE" --containers
kubectl top node "$NODE"
```

These require Metrics Server or another resource metrics API. They do not expose
raw cgroup throttling counters or reliably explain a past OOM.

## Termination And Eviction

```bash
kubectl -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\t"}{.lastState.terminated.reason}{"\t"}{.lastState.terminated.exitCode}{"\t"}{.lastState.terminated.finishedAt}{"\n"}{end}'
kubectl -n "$NAMESPACE" describe pod "$POD"
kubectl describe node "$NODE"
kubectl get events -A --sort-by=.metadata.creationTimestamp \
  --field-selector reason=Evicted
```

For cgroup or kernel evidence, first discover the node OS, runtime, cgroup
version, and Pod/container IDs. Node debug access is privileged and should use
the environment's approved path.
