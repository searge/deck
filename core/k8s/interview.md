---
title: Kubernetes Interview Checkpoints
tags:
  - kubernetes
  - interviews
  - troubleshooting
  - platform-engineering
aliases:
  - Kubernetes Interview Guide
description: Mechanism-first Kubernetes interview checkpoints with evidence expected from senior answers.
---

# Kubernetes Interview Checkpoints

Use these prompts to find the first boundary that cannot be explained. A strong
answer names state owners, asynchronous transitions, failure modes and evidence;
it does not recite object definitions.

> [!info] Method
> Answer each prompt in three passes: whiteboard the path, identify the failed
> invariant, then name read-only evidence. Commands come last.

## Core API And Reconciliation

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| What happens after `kubectl apply`? | discovery, authn/authz, admission, persistence, independent watches and reconcilers | [API Machinery](api_machinery.md) |
| Why can status lag spec? | separate writers, observed generation, cached watches, retries and stale reads | [Reconciliation](reconciliation.md) |
| Why are controllers level-triggered? | missed/duplicate events, idempotence, desired versus observed state | [Reconciliation](reconciliation.md) |
| What does etcd loss break? | API persistence/reads, quorum, already-running node workloads and lease/status effects | [Control Plane](control_plane.md) |
| Why is `kubectl get all` incomplete? | discovery and API resources, not a complete inventory primitive | [API Machinery](api_machinery.md) |

Checkpoint: draw one Deployment update with object owners, revisions and the
writers of each status field.

## Scheduling, Resources And Nodes

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| Why is a Pod `Pending`? | queue, filters, requests, constraints, volume topology, Events as evidence | [Scheduling](scheduling.md) |
| Requests versus limits? | scheduling/accounting versus runtime enforcement, CPU throttling, memory OOM | [Resources](resources.md) |
| Pod OOM versus node eviction? | cgroup limit, kernel victim, QoS, pressure signals and kubelet policy | [Resources](resources.md) |
| Cordon versus drain? | scheduling exclusion versus Eviction API, PDBs, DaemonSets and local data | [Node Lifecycle](node_lifecycle.md) |
| Node heartbeat disappears? | Lease, Node status, conditions, taints, tolerations and delayed eviction | [Node Lifecycle](node_lifecycle.md) |

Checkpoint: diagnose high load average with low CPU and explain which Kubernetes
resource settings do not solve blocked I/O.

## Workloads And Storage

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| Deployment versus StatefulSet? | replaceable replicas versus stable identity, ordering and volume attachment | [Object To Running Pod](object_to_running_pod.md) |
| Readiness versus liveness? | traffic admission versus restart, startup protection and dependency failure | [Pod Lifecycle](pod_lifecycle.md) |
| What does a PDB guarantee? | voluntary disruption budget, not replica health or involuntary failure prevention | [Node Lifecycle](node_lifecycle.md) |
| PVC is `Pending`? | class, provisioner, binding mode, topology, quota and backend capacity | [Storage](storage.md) |
| PVC is bound, Pod is stuck? | attach, stage, mount, node topology, filesystem and runtime boundaries | [Storage](storage.md) |
| Why `Multi-Attach`? | access mode, existing attachment, node ownership and CSI/backend state | [Storage](storage.md) |

Checkpoint: trace one stateful Pod replacement through scheduler topology,
VolumeAttachment where applicable, CSI controller/node calls and filesystem
mount without treating a bound PVC as mounted storage.

## Security And Extension Points

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| Authentication versus authorization versus admission? | identity, permitted action, request mutation/validation and ordering | [API Machinery](api_machinery.md) |
| Is a Secret encrypted? | base64 is encoding; API/etcd encryption, access, projection and external stores differ | [Professional Roadmap](roadmap.md) |
| How to debug `Forbidden`? | exact identity, verb, group/resource/subresource, namespace and RBAC aggregation | [API Machinery](api_machinery.md) |
| Why use a finalizer? | external cleanup, deletion timestamp, idempotence and escape procedure | [Reconciliation](reconciliation.md) |
| CRD plus controller? | API schema is data; reconciler supplies behavior, status, retries and ownership | [Reconciliation](reconciliation.md) |
| Webhook unavailable? | admission dependency, timeout/failure policy, rollout and API availability risk | [Control Plane](control_plane.md) |

Checkpoint: design a controller that creates an external resource and survives
duplicate events, stale cache, partial creation, deletion and API write conflict.

## Networking Foundations

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| How do two Pods communicate on one node? | netns, veth, route/bridge or implementation hook, return path | [Packet Path](networking/packet_path.md) |
| How do Pods communicate across nodes? | Pod CIDR reachability, overlay or native routing, MTU and reverse path | [Packet Path](networking/packet_path.md) |
| What does CNI do? | runtime invocation, stdin/env contract, ADD/DEL/CHECK, IPAM and rollback | [CNI](networking/cni.md) |
| Does CNI carry every packet? | no: plugins configure state; kernel/programs/proxies carry traffic afterward | [CNI](networking/cni.md) |
| Pod IP works, ClusterIP fails? | Service/EndpointSlice graph, active dataplane, node-local state and conntrack | [Service Dataplane](networking/service_dataplane.md) |
| DNS works, connection fails? | discovery is not routing; endpoint, listener, policy and return path remain | [Kubernetes DNS](networking/dns.md) |
| Why can policy allow still fail? | ingress/egress isolation are independent and policy rules are additive | [NetworkPolicy](networking/network_policy.md) |

Checkpoint: whiteboard a request from one Pod to a remote Pod through a
ClusterIP. Branch the answer for iptables, nftables and eBPF without claiming
that Kubernetes mandates one.

## Cilium And eBPF

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| What is an eBPF program? | verified kernel program, attachment hook, context, helpers and maps | [eBPF And Cilium](networking/ebpf_cilium.md) |
| What are BPF maps for? | shared state between programs/userspace, key/value lifecycle and capacity | [eBPF And Cilium](networking/ebpf_cilium.md) |
| XDP versus tc versus cgroup/socket? | different hook locations and contexts, not a speed ranking | [eBPF And Cilium](networking/ebpf_cilium.md) |
| How can Cilium replace kube-proxy? | agents observe Services/EndpointSlices and program BPF service state/hooks | [eBPF And Cilium](networking/ebpf_cilium.md) |
| Why is migration risky? | independent NAT/connection state, kernel requirements and rollback ordering | [eBPF And Cilium](networking/ebpf_cilium.md) |
| What does Hubble prove? | observed Cilium flow/verdict; not application correctness or complete packet path | [eBPF And Cilium](networking/ebpf_cilium.md) |

Checkpoint: start from one denied flow and connect Kubernetes labels to Cilium
identity, policy state, hook, verdict and packet capture.

## Envoy, Istio And Sidecars

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| Envoy listener versus cluster? | downstream accept/filter path versus upstream destination pool | [Service Mesh](service_mesh.md) |
| What is xDS? | dynamic discovery APIs and control-plane configuration, not user traffic | [Service Mesh](service_mesh.md) |
| Sidecar costs and failure modes? | per-Pod CPU/memory, startup/termination, capture, config fan-out, Jobs | [Service Mesh](service_mesh.md) |
| Native Kubernetes sidecar? | restartable init container lifecycle, not synonymous with mesh injection | [Service Mesh](service_mesh.md) |
| Istio ambient versus sidecar? | per-node L4 ztunnel, optional L7 waypoint, changed policy/telemetry path | [Service Mesh](service_mesh.md) |
| Retry, timeout and circuit breaker? | request budget, amplification, connection pools and failure classification | [Service Mesh](service_mesh.md) |

Checkpoint: explain an HTTP 503 by separating application response, Envoy route,
cluster warming, endpoint health, reset and Kubernetes readiness.

## Tracing And Observability

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| Trace versus metric versus log? | causal request path, aggregation, discrete events and correlation fields | [Observability](observability.md) |
| Why is a trace broken? | context injection/extraction, async boundaries, sampling and proxy/app ownership | [Observability](observability.md) |
| Head versus tail sampling? | decision point, completeness, buffer cost, latency and overload behavior | [Observability](observability.md) |
| Why avoid PII in baggage? | propagation across trust boundaries and unintended logs/exports | [Observability](observability.md) |
| What should run at the edge? | local buffering/filtering, bounded cardinality, backpressure and store-forward | [Observability](observability.md) |

Checkpoint: reconstruct one slow request with a trace ID and prove whether time
was spent in queueing, network, proxy, application, storage or telemetry itself.

## Edge And Miltech Systems

| Prompt | Senior-level answer must include | Study |
| --- | --- | --- |
| What survives cloud disconnection? | existing local state, control loops present on node, missing API dependencies | [Edge Kubernetes](edge.md) |
| How are images delivered offline? | pinned OCI artifacts, architecture variants, local registry/cache, verification | [Edge Kubernetes](edge.md) |
| How do 500 nodes upgrade? | cohorts, compatibility, bandwidth, health gates, pause, rollback and audit | [Edge Kubernetes](edge.md) |
| What about device failure? | plugin/DRA health, allocation ownership, workload response and node recovery | [Edge Kubernetes](edge.md) |
| Why does clock matter? | certificate validity, logs/traces, leases, distributed ordering and GNSS loss | [Edge Kubernetes](edge.md) |
| K3s versus KubeEdge? | lightweight distribution versus cloud-edge architecture; workload requirements first | [Edge Kubernetes](edge.md) |

Checkpoint: design degraded operation for loss of cloud link, registry, DNS and
time source. Name the local authority and recovery evidence for each.

## Scoring

| Level | Observable answer quality |
| --- | --- |
| 0 | names a command or product only |
| 1 | describes the happy path |
| 2 | names owners, state and asynchronous boundaries |
| 3 | derives failure modes and ordered evidence |
| 4 | compares implementations, migration risks and rollback proof |

Record the first prompt below level 3. That prompt selects the next stage in
the [Professional Roadmap](roadmap.md).
