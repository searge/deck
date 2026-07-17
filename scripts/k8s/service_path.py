#!/usr/bin/env python3
"""Trace Service selection and EndpointSlice state from structured data.

The tracer stops at the Kubernetes API boundary. It does not infer whether the
node uses iptables, nftables, IPVS, eBPF, or another Service dataplane.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_FIXTURE = Path(__file__).with_name("fixtures") / "service_path.json"


class TraceError(ValueError):
    """Input does not satisfy the selector-backed Service trace contract."""


@dataclass(frozen=True, slots=True)
class PodMatch:
    name: str
    uid: str
    ip: str | None
    ready: bool | None


@dataclass(frozen=True, slots=True)
class Endpoint:
    addresses: tuple[str, ...]
    pod_name: str | None
    pod_uid: str | None
    ready: bool | None
    serving: bool | None
    terminating: bool | None
    effective_ready: bool
    effective_serving: bool
    effective_terminating: bool


@dataclass(frozen=True, slots=True)
class ServiceTrace:
    namespace: str
    service: str
    cluster_ip: str | None
    selector: dict[str, str]
    ports: tuple[str, ...]
    endpoint_ports: tuple[str, ...]
    matched_pods: tuple[PodMatch, ...]
    endpoints: tuple[Endpoint, ...]
    warnings: tuple[str, ...]


def _metadata_name(obj: dict[str, Any], kind: str) -> str:
    metadata = obj.get("metadata")
    if not isinstance(metadata, dict) or not metadata.get("name"):
        raise TraceError(f"{kind} has no metadata.name")
    return str(metadata["name"])


def _pod_ready(pod: dict[str, Any]) -> bool | None:
    status = pod.get("status", {})
    conditions = status.get("conditions", [])
    if not isinstance(conditions, list):
        return None
    for condition in conditions:
        if isinstance(condition, dict) and condition.get("type") == "Ready":
            value = condition.get("status")
            if value == "True":
                return True
            if value == "False":
                return False
            return None
    return None


def _raw_condition(conditions: dict[str, Any], name: str) -> bool | None:
    value = conditions.get(name)
    return value if isinstance(value, bool) else None


def _matches(labels: object, selector: dict[str, str]) -> bool:
    if not isinstance(labels, dict):
        return False
    return all(labels.get(key) == value for key, value in selector.items())


def _service_ports(service: dict[str, Any]) -> tuple[str, ...]:
    spec = service.get("spec", {})
    ports = spec.get("ports", [])
    if not isinstance(ports, list) or not ports:
        raise TraceError("Service has no spec.ports")

    rendered: list[str] = []
    for port in ports:
        if not isinstance(port, dict) or "port" not in port:
            raise TraceError("Service contains an invalid port entry")
        protocol = port.get("protocol", "TCP")
        target = port.get("targetPort", port["port"])
        name = f"{port.get('name')}:" if port.get("name") else ""
        rendered.append(f"{name}{port['port']}->{target}/{protocol}")
    return tuple(rendered)


def trace_objects(
    service: dict[str, Any],
    pods: list[dict[str, Any]],
    endpoint_slices: list[dict[str, Any]],
) -> ServiceTrace:
    """Build a bounded Service-to-Pod and EndpointSlice trace."""
    name = _metadata_name(service, "Service")
    metadata = service.get("metadata", {})
    namespace = str(metadata.get("namespace", "default"))
    spec = service.get("spec", {})

    if spec.get("type") == "ExternalName":
        raise TraceError("ExternalName Service has no selector-backed path")

    selector_obj = spec.get("selector")
    if not isinstance(selector_obj, dict) or not selector_obj:
        raise TraceError(
            "Service is selectorless; trace its managed endpoints"
        )
    selector = {str(key): str(value) for key, value in selector_obj.items()}

    matched: list[PodMatch] = []
    matched_uids: set[str] = set()
    for pod in pods:
        pod_metadata = pod.get("metadata", {})
        if pod_metadata.get("namespace", "default") != namespace:
            continue
        if not _matches(pod_metadata.get("labels"), selector):
            continue
        uid = str(pod_metadata.get("uid", ""))
        if uid:
            matched_uids.add(uid)
        status = pod.get("status", {})
        matched.append(
            PodMatch(
                name=_metadata_name(pod, "Pod"),
                uid=uid,
                ip=str(status["podIP"]) if status.get("podIP") else None,
                ready=_pod_ready(pod),
            )
        )

    endpoints: list[Endpoint] = []
    endpoint_ports: set[str] = set()
    for endpoint_slice in endpoint_slices:
        slice_metadata = endpoint_slice.get("metadata", {})
        labels = slice_metadata.get("labels", {})
        if slice_metadata.get("namespace", "default") != namespace:
            continue
        if not isinstance(labels, dict):
            continue
        if labels.get("kubernetes.io/service-name") != name:
            continue
        for port in endpoint_slice.get("ports", []):
            if not isinstance(port, dict) or port.get("port") is None:
                continue
            protocol = port.get("protocol", "TCP")
            port_name = f"{port.get('name')}:" if port.get("name") else ""
            endpoint_ports.add(f"{port_name}{port['port']}/{protocol}")
        for endpoint in endpoint_slice.get("endpoints", []):
            if not isinstance(endpoint, dict):
                continue
            conditions = endpoint.get("conditions", {})
            target = endpoint.get("targetRef", {})
            addresses = endpoint.get("addresses", [])
            if not isinstance(conditions, dict):
                conditions = {}
            if not isinstance(target, dict):
                target = {}
            if not isinstance(addresses, list):
                addresses = []
            ready = _raw_condition(conditions, "ready")
            serving = _raw_condition(conditions, "serving")
            terminating = _raw_condition(conditions, "terminating")
            endpoints.append(
                Endpoint(
                    addresses=tuple(str(address) for address in addresses),
                    pod_name=(
                        str(target["name"]) if target.get("name") else None
                    ),
                    pod_uid=(
                        str(target["uid"]) if target.get("uid") else None
                    ),
                    ready=ready,
                    serving=serving,
                    terminating=terminating,
                    effective_ready=True if ready is None else ready,
                    effective_serving=True if serving is None else serving,
                    effective_terminating=(
                        False if terminating is None else terminating
                    ),
                )
            )

    warnings: list[str] = []
    if not matched:
        warnings.append("selector matches no Pods")
    if not endpoints:
        warnings.append("no EndpointSlice endpoints found")
    elif not endpoint_ports:
        warnings.append("EndpointSlices have no resolved ports")
    if any(not endpoint.effective_ready for endpoint in endpoints):
        warnings.append("one or more endpoints have ready=false")
    foreign = {
        endpoint.pod_uid
        for endpoint in endpoints
        if endpoint.pod_uid and endpoint.pod_uid not in matched_uids
    }
    if foreign:
        warnings.append(
            "EndpointSlice references Pods outside current matches"
        )

    cluster_ip = spec.get("clusterIP")
    return ServiceTrace(
        namespace=namespace,
        service=name,
        cluster_ip=(
            str(cluster_ip) if cluster_ip and cluster_ip != "None" else None
        ),
        selector=selector,
        ports=_service_ports(service),
        endpoint_ports=tuple(sorted(endpoint_ports)),
        matched_pods=tuple(sorted(matched, key=lambda pod: pod.name)),
        endpoints=tuple(
            sorted(
                endpoints,
                key=lambda endpoint: (
                    endpoint.pod_name or "",
                    endpoint.addresses,
                ),
            )
        ),
        warnings=tuple(warnings),
    )


def load_fixture(path: Path) -> ServiceTrace:
    """Load one fixture containing Service, Pod, and EndpointSlice objects."""
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    return trace_objects(
        service=data["service"],
        pods=data["pods"],
        endpoint_slices=data["endpointSlices"],
    )


def _kubectl_json(args: list[str], timeout: float) -> dict[str, Any]:
    completed = subprocess.run(
        ["kubectl", *args, "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    value: dict[str, Any] = json.loads(completed.stdout)
    return value


def load_live(
    namespace: str, service_name: str, timeout: float
) -> ServiceTrace:
    """Read the three object sets from kubectl without mutating the cluster."""
    service = _kubectl_json(
        ["-n", namespace, "get", "service", service_name], timeout
    )
    selector_obj = service.get("spec", {}).get("selector")
    if not isinstance(selector_obj, dict) or not selector_obj:
        return trace_objects(service, [], [])
    selector = ",".join(
        f"{key}={value}" for key, value in sorted(selector_obj.items())
    )
    pods_obj = _kubectl_json(
        ["-n", namespace, "get", "pods", "-l", selector], timeout
    )
    slices_obj = _kubectl_json(
        [
            "-n",
            namespace,
            "get",
            "endpointslices",
            "-l",
            f"kubernetes.io/service-name={service_name}",
        ],
        timeout,
    )
    return trace_objects(
        service,
        list(pods_obj.get("items", [])),
        list(slices_obj.get("items", [])),
    )


def format_trace(trace: ServiceTrace) -> str:
    """Render a compact human-readable trace."""
    selector = ",".join(
        f"{key}={value}" for key, value in trace.selector.items()
    )
    lines = [
        f"service: {trace.namespace}/{trace.service}",
        f"clusterIP: {trace.cluster_ip or '<headless>'}",
        f"selector: {selector}",
        f"ports: {', '.join(trace.ports)}",
        f"EndpointSlice ports: {', '.join(trace.endpoint_ports) or '<none>'}",
        "matched Pods:",
    ]
    lines.extend(
        f"  {pod.name} uid={pod.uid or '<missing>'} "
        f"ip={pod.ip or '<pending>'} ready={pod.ready}"
        for pod in trace.matched_pods
    )
    lines.append("EndpointSlice endpoints:")
    lines.extend(
        f"  {endpoint.pod_name or '<no targetRef>'} "
        f"addresses={','.join(endpoint.addresses)} "
        f"ready={endpoint.effective_ready}(raw={endpoint.ready}) "
        f"serving={endpoint.effective_serving}(raw={endpoint.serving}) "
        f"terminating={endpoint.effective_terminating}"
        f"(raw={endpoint.terminating})"
        for endpoint in trace.endpoints
    )
    if trace.warnings:
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in trace.warnings)
    lines.append(
        "boundary: API objects only; inspect the active node dataplane next"
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trace a selector-backed Service through EndpointSlices."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="offline JSON fixture (default: bundled fixture)",
    )
    source.add_argument(
        "--live",
        action="store_true",
        help="read current objects using kubectl; never mutates the cluster",
    )
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--service")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.live:
            if not args.service:
                raise TraceError("--live requires --service")
            trace = load_live(args.namespace, args.service, args.timeout)
        else:
            trace = load_fixture(args.fixture)
    except TraceError as error:
        raise SystemExit(f"trace error: {error}") from error
    except subprocess.TimeoutExpired as error:
        raise SystemExit(
            f"kubectl timed out after {error.timeout}s"
        ) from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or str(error)
        raise SystemExit(f"kubectl failed: {detail}") from error
    except FileNotFoundError as error:
        raise SystemExit(
            f"command or fixture not found: {error.filename}"
        ) from error

    if args.as_json:
        print(json.dumps(asdict(trace), indent=2, sort_keys=True))
    else:
        print(format_trace(trace))


if __name__ == "__main__":
    main()
