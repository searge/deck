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

## Trace Service Objects

The offline fixture is the default and requires no cluster:

```bash
uv run python scripts/k8s/service_path.py
uv run python scripts/k8s/service_path.py --json
```

Read-only live mode uses structured `kubectl -o json` responses:

```bash
uv run python scripts/k8s/service_path.py \
  --live --namespace "$NAMESPACE" --service "$SERVICE"
```

The tracer stops after Service, selected Pods and EndpointSlices. Continue with
the active node implementation; it does not claim that API intent reached the
kernel.

## Node Packet Evidence

> [!warning] Privileged evidence
> Node shell, namespace entry, packet capture, conntrack and BPF inspection can
> expose tenant traffic. Use the approved incident path and a narrow filter.

After identifying the source and destination Pod IPs and nodes:

```bash
ip route get "$DESTINATION_IP" from "$SOURCE_IP"
ip neigh show
ss -Htanp
timeout 20 tcpdump -ni any \
  "host $SOURCE_IP and host $DESTINATION_IP and port $PORT"
```

Compare the forward and return path. A capture on only one interface does not
locate a drop.

## Implementation-Specific Branches

| Discovered dataplane | Continue with |
| --- | --- |
| kube-proxy iptables | version-matched netfilter rules, counters and conntrack |
| kube-proxy nftables | nftables rules/maps and kube-proxy metrics |
| kube-proxy IPVS | IPVS virtual services plus supporting netfilter state |
| Cilium kube-proxy replacement | endpoint identity, service maps and Hubble flow |
| service mesh | accepted listener, route, cluster and endpoint configuration |

Read [Packet Path](k8s/networking/packet_path.md), [Service Dataplane](k8s/networking/service_dataplane.md), [NetworkPolicy](k8s/networking/network_policy.md), and [eBPF And Cilium](k8s/networking/ebpf_cilium.md) before selecting commands for one implementation.
