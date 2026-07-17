---
title: Kubernetes API Observation
tags:
  - kubernetes
  - api
  - troubleshooting
aliases:
  - kubectl API Debugging
description: Read-only discovery, authorization, field ownership, revisions, health, and watch checks.
---

# Kubernetes API Observation

Confirm context first, then separate discovery, authentication, authorization,
admission, concurrency, and API availability. See
[API Machinery](k8s/api_machinery.md) for the model.

## Discovery And Scope

```bash
kubectl version
kubectl api-versions
kubectl api-resources --sort-by=name
kubectl explain deployment.spec.strategy
kubectl get --raw /api
kubectl get --raw /apis
```

## Authorization

```bash
kubectl auth whoami
kubectl auth can-i get pods -n "$NAMESPACE"
kubectl auth can-i patch deployments.apps -n "$NAMESPACE"
kubectl auth can-i --list -n "$NAMESPACE"
```

`can-i` evaluates authorization. It does not test admission or a controller's
later ability to converge.

## Revisions And Field Ownership

```bash
kubectl -n "$NAMESPACE" get deploy "$DEPLOYMENT" \
  -o jsonpath='{.metadata.uid}{"\t"}{.metadata.resourceVersion}{"\t"}{.metadata.generation}{"\n"}'
kubectl -n "$NAMESPACE" get deploy "$DEPLOYMENT" -o yaml --show-managed-fields
kubectl -n "$NAMESPACE" get deploy "$DEPLOYMENT" \
  -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"\t"}{.operation}{"\t"}{.subresource}{"\n"}{end}'
```

Do not use `--force-conflicts` until the intended field owner is explicit.

## Health And Watch

```bash
kubectl get --raw /livez?verbose
kubectl get --raw /readyz?verbose
kubectl get pods -A --watch-only --output-watch-events
```

Stop the foreground watch with `Ctrl-C`. A reconnect or relist is normal watch
client behavior; repeated churn needs API, network, and revision evidence.

## Mutating Request Preview

> [!warning] Server-side dry run contacts admission
> It should not persist the object, but external webhooks still receive the
> admission request and must be treated as external dependencies.

```bash
kubectl apply --server-side --dry-run=server -f manifest.yaml -o yaml
kubectl diff --server-side -f manifest.yaml
```
