---
title: Kubernetes Node Maintenance
tags:
  - kubernetes
  - nodes
  - operations
aliases:
  - Kubernetes Drain
description: Read-before-mutate checks for cordon, drain, and uncordon operations.
---

# Kubernetes Node Maintenance

Node maintenance crosses scheduling, disruption, storage, and application
availability. Read [Node Lifecycle](k8s/node_lifecycle.md) before treating
`drain` as a single operation.

## Preflight: Read-Only

```bash
kubectl get node "$NODE" -o wide
kubectl describe node "$NODE"
kubectl get lease -n kube-node-lease "$NODE" -o yaml
kubectl get pods -A --field-selector spec.nodeName="$NODE" -o wide
kubectl get pdb -A
kubectl get volumeattachment -o wide
```

Identify DaemonSets, unmanaged Pods, local data, single replicas, quorum
members, topology constraints, and single-writer volumes before proceeding.

## Cordon

> [!warning] Mutation
> Cordon blocks ordinary new scheduling but leaves existing Pods in place.

```bash
kubectl cordon "$NODE"
kubectl get node "$NODE"
```

## Dry-Run Drain

```bash
kubectl drain "$NODE" --dry-run=server
```

Review the exact client/server version behavior and output. Do not add
`--ignore-daemonsets`, `--delete-emptydir-data`, `--disable-eviction`, or
`--force` until the consequence is explicitly accepted for this node.

## Drain And Return

> [!danger] Disruptive mutation
> The flags below are intentionally not supplied. Choose them from the preflight
> evidence and workload policy, then watch replacement readiness and storage
> detach/attach behavior.

```bash
kubectl drain "$NODE" REQUIRED_REVIEWED_FLAGS
kubectl get pods -A --field-selector spec.nodeName="$NODE" -o wide
```

After maintenance, validate kubelet, runtime, network, storage, Node conditions,
and Lease renewal before returning capacity:

```bash
kubectl uncordon "$NODE"
kubectl get node "$NODE" -o wide
```
