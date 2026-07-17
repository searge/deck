---
title: Kubernetes Troubleshooting
tags:
  - kubernetes
  - troubleshooting
  - kubectl
aliases:
  - Kubernetes Triage
description: A symptom-first, read-only evidence ladder from owner to Pod, node, network, and storage.
---

# Kubernetes Troubleshooting

Capture identity and current state before changing anything. Names are reusable,
Events expire, and consecutive commands are not an atomic snapshot.

## Evidence Ladder

```bash
kubectl config current-context
kubectl -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{.metadata.uid}{"\t"}{.metadata.resourceVersion}{"\t"}{.spec.nodeName}{"\n"}'
kubectl -n "$NAMESPACE" get pod "$POD" -o wide
kubectl -n "$NAMESPACE" describe pod "$POD"
kubectl -n "$NAMESPACE" get pod "$POD" -o json
```

Then follow the failed boundary:

| Observation | Continue with |
| --- | --- |
| no Pod object | owner chain: Deployment, ReplicaSet, Job, StatefulSet |
| no `spec.nodeName` | scheduling Events, requests, affinity, taints, PVC topology |
| assigned, container waiting | image, referenced config, CNI, CSI, runtime Events |
| repeated restart | previous state and `logs --previous` |
| ready, no Service traffic | selector and EndpointSlice conditions |
| deletion timestamp remains | finalizers, node reachability, volume path |

## Owner Chain

```bash
kubectl -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{range .metadata.ownerReferences[*]}{.apiVersion}{"\t"}{.kind}{"\t"}{.name}{"\t"}{.uid}{"\n"}{end}'
kubectl -n "$NAMESPACE" get deploy,rs,pod --show-labels
```

Owner references establish lifecycle. Labels establish selection. Do not infer
ownership from a shared name prefix.

## Container Failure

```bash
kubectl -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\t"}{.state}{"\t"}{.lastState}{"\t"}{.restartCount}{"\n"}{end}'
kubectl -n "$NAMESPACE" logs "$POD" --all-containers --timestamps
kubectl -n "$NAMESPACE" logs "$POD" --all-containers --previous --timestamps
```

## Avoid Premature Mutation

Restarting a Pod, deleting an object, force-removing a finalizer, or draining a
node can destroy the evidence needed to distinguish controller, node, network,
and storage failures. Record UID, status, Events, and relevant component logs
first.

The full transition map is in
[Object To Running Pod](k8s/object_to_running_pod.md).
