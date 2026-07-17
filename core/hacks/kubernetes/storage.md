---
title: Kubernetes Storage Triage
tags:
  - kubernetes
  - storage
  - troubleshooting
aliases:
  - Kubernetes PVC Debugging
description: An ordered read-only trace across PVC, PV, StorageClass, scheduling, CSI, and backend state.
---

# Kubernetes Storage Triage

Follow the volume lifecycle in order. `Bound` is only one transition; see
[Storage](k8s/storage.md).

## Claim To Volume

```bash
kubectl -n "$NAMESPACE" get pvc "$CLAIM" -o yaml
kubectl -n "$NAMESPACE" describe pvc "$CLAIM"
kubectl get storageclass -o yaml
kubectl get pv "$VOLUME" -o yaml
```

Record StorageClass, binding mode, provisioner, access/volume modes, capacity,
reclaim policy, claim UID, volume handle, node affinity, conditions, and Events.

## Pod And Node Path

```bash
kubectl -n "$NAMESPACE" get pod "$POD" -o yaml
kubectl -n "$NAMESPACE" describe pod "$POD"
kubectl get volumeattachment -o wide
kubectl get csidriver,csinode -o yaml
```

No `VolumeAttachment` can be correct for a driver that does not require attach.
Discover the CSI deployment and capabilities before escalating to its logs.

## Snapshots

```bash
kubectl api-resources | rg 'volumesnapshot'
kubectl get volumesnapshot,volumesnapshotcontent -A
```

These resources are optional. Snapshot readiness is not proof of application
consistency or off-site backup.

## Recovery Boundary

> [!danger] Data-risk mutations
> Do not delete PVC/PV/VolumeAttachment objects, change reclaim policy, remove
> protection finalizers, force-detach, or manipulate the backend until object
> identity, driver ownership, node fencing, and data consequences are explicit.
