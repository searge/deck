---
title: Kubernetes Control-Plane Triage
tags:
  - kubernetes
  - control-plane
  - troubleshooting
aliases:
  - Control Plane Triage
description: Bounded health, latency, flow-control, Lease, and component checks.
---

# Kubernetes Control-Plane Triage

Use this when many unrelated resources or controllers slow down together. The
failure model is in [Control Plane](k8s/control_plane.md).

## API Boundary

```bash
time kubectl get --raw /livez?verbose
time kubectl get --raw /readyz?verbose
time kubectl get --raw /version
kubectl cluster-info
```

Compare failures through the normal API endpoint with the platform's supported
direct health path. Do not disable TLS verification as a diagnostic shortcut.

## Coordination And Flow Control

```bash
kubectl get lease -A
kubectl get flowschema,prioritylevelconfiguration
kubectl get apiservice
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration
```

A configuration object does not prove its backing webhook or aggregated API is
healthy. Correlate matching request latency and failure policy.

## Focus Metrics

Access depends on RBAC. Avoid retaining the full metrics response when a filter
is enough:

```bash
kubectl get --raw /metrics | rg '^(apiserver_request_total|apiserver_request_duration_seconds|apiserver_flowcontrol_|etcd_request_duration_seconds)'
```

Metric names and stability levels vary by Kubernetes release. Treat an absent
series as a version/configuration question, not proof of zero activity.

## Self-Managed Branch

Only after confirming how the cluster is deployed:

```bash
kubectl -n kube-system get pods -o wide
kubectl -n kube-system get events --sort-by=.metadata.creationTimestamp
```

Static control-plane Pods, systemd units, container runtime commands, and etcd
endpoint tools are distribution-specific. Snapshot or membership changes are
recovery operations and intentionally omitted here.
