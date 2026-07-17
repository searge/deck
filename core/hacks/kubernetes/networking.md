---
title: Kubernetes Networking Triage
tags:
  - kubernetes
  - networking
  - troubleshooting
aliases:
  - Kubernetes Service Debugging
description: An ordered read-only trace from process and Pod IP to Service, EndpointSlice, DNS, and policy.
---

# Kubernetes Networking Triage

Work from application to discovery to dataplane. See
[Networking](k8s/networking.md) for the layer boundaries.

## Object Trace

```bash
kubectl -n "$NAMESPACE" get service "$SERVICE" -o yaml
kubectl -n "$NAMESPACE" get pods -l "$SELECTOR" -o wide --show-labels
kubectl -n "$NAMESPACE" get endpointslice \
  -l kubernetes.io/service-name="$SERVICE" -o yaml
kubectl -n "$NAMESPACE" get networkpolicy -o yaml
```

Compare Service `port`/`targetPort`, Pod labels and declared ports, Pod readiness,
and EndpointSlice addresses/conditions. A selector string copied from memory is
not evidence; read it from the Service.

## DNS And In-Pod Checks

> [!warning] Executes inside a workload
> Prefer an existing diagnostic Pod approved for the namespace. An ephemeral
> debug container or newly created Pod is a mutation and may be blocked by
> policy.

```bash
kubectl -n "$NAMESPACE" exec "$CLIENT_POD" -- cat /etc/resolv.conf
kubectl -n "$NAMESPACE" exec "$CLIENT_POD" -- getent hosts \
  "$SERVICE.$NAMESPACE.svc.cluster.local"
```

Tool availability varies by image. Record the exact name, response, source Pod,
and destination port.

## Discover Implementations

```bash
kubectl -n kube-system get daemonset,deployment -o wide
kubectl get ingressclass,gatewayclass
kubectl get service "$SERVICE" -n "$NAMESPACE" \
  -o jsonpath='{.spec.type}{"\t"}{.status.loadBalancer}{"\n"}'
```

Only then choose CNI, Service dataplane, DNS, Ingress, Gateway, or cloud-specific
logs and node tools. Do not assume `iptables` from the presence of a Service.
