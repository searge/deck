---
tags:
  - kubernetes
  - snippets
aliases:
  - Kubernetes hacks
title: Kubernetes Hacks
description: Symptom-first kubectl, API, node, resource, network, and storage operations.
---

# Kubernetes Hacks

These pages are operational entry points. The corresponding
[Kubernetes Internals](k8s/k8s.md) module explains why the evidence is
useful and where each command sits in the control loop.

## Start Read-Only

```bash
kubectl version --client
kubectl cluster-info
kubectl get nodes -o wide
kubectl config current-context
kubectl config view --minify
```

Confirm context and namespace before every mutation. `kubectl get all -A` is
not a complete inventory; use API discovery when resource coverage matters.

## Route By Symptom

| Symptom | Commands | Internals |
| --- | --- | --- |
| rejected request, conflict, watch/API issue | [API observation](api.md) | [API machinery](k8s/api_machinery.md) |
| Pod missing, Pending, restarting, or terminating | [troubleshooting](troubleshooting.md) | [object to running Pod](k8s/object_to_running_pod.md) |
| broad API/control-loop slowdown | [control plane](control_plane.md) | [control plane](k8s/control_plane.md) |
| node health or planned maintenance | [node maintenance](node_maintenance.md) | [node lifecycle](k8s/node_lifecycle.md) |
| scheduling, throttling, OOM, or eviction | [resources](resources.md) | [resource internals](k8s/resources.md) |
| Service, EndpointSlice, DNS, or policy | [networking](networking.md) | [network internals](k8s/networking.md) |
| CNI, packet path, eBPF, mesh, or edge networking | [networking](networking.md) | [professional roadmap](k8s/roadmap.md) |
| PVC, PV, attach, mount, or snapshot | [storage](storage.md) | [storage internals](k8s/storage.md) |

General tools: [kubectl](kubectl.md), [Helm](helm.md).

## Context And Namespace

```bash
kubectl config get-contexts
kubectl get namespaces
kubectl config view --minify -o jsonpath='{..namespace}{"\n"}'
```

> [!warning] Mutates local kubeconfig
> These commands do not mutate the cluster, but they change which cluster or
> namespace later commands target.

```bash
kubectl config use-context "$CONTEXT"
kubectl config set-context --current --namespace "$NAMESPACE"
```
