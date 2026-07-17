from __future__ import annotations

import unittest

from scripts.k8s.service_path import (
    DEFAULT_FIXTURE,
    TraceError,
    load_fixture,
    trace_objects,
)


class ServicePathTest(unittest.TestCase):
    def test_fixture_traces_matches_and_endpoint_conditions(self) -> None:
        trace = load_fixture(DEFAULT_FIXTURE)

        self.assertEqual(trace.service, "web")
        self.assertEqual(trace.cluster_ip, "10.96.0.42")
        self.assertEqual(trace.endpoint_ports, ("http:8080/TCP",))
        self.assertEqual(
            [pod.name for pod in trace.matched_pods], ["web-a", "web-b"]
        )
        self.assertEqual(
            [endpoint.ready for endpoint in trace.endpoints], [True, False]
        )
        self.assertIn("one or more endpoints have ready=false", trace.warnings)

    def test_selectorless_service_is_rejected(self) -> None:
        service = {
            "metadata": {"name": "external", "namespace": "demo"},
            "spec": {"ports": [{"port": 80}]},
        }

        with self.assertRaisesRegex(TraceError, "selectorless"):
            trace_objects(service, [], [])

    def test_unknown_pod_readiness_remains_unknown(self) -> None:
        trace = load_fixture(DEFAULT_FIXTURE)
        pod = {
            "metadata": {
                "name": "web-unknown",
                "namespace": "demo",
                "labels": {"app": "web"},
                "uid": "pod-unknown",
            },
            "status": {"conditions": [{"type": "Ready", "status": "Unknown"}]},
        }

        result = trace_objects(
            {
                "metadata": {"name": "web", "namespace": "demo"},
                "spec": {
                    "ports": [{"port": 80}],
                    "selector": {"app": "web"},
                },
            },
            [pod],
            [],
        )

        self.assertIsNone(result.matched_pods[0].ready)
        self.assertEqual(trace.matched_pods[0].ready, True)

    def test_nil_endpoint_conditions_use_api_defaults(self) -> None:
        service = {
            "metadata": {"name": "web", "namespace": "demo"},
            "spec": {
                "ports": [{"port": 80}],
                "selector": {"app": "web"},
            },
        }
        endpoint_slice = {
            "metadata": {
                "namespace": "demo",
                "labels": {"kubernetes.io/service-name": "web"},
            },
            "ports": [{"port": 8080}],
            "endpoints": [{"addresses": ["10.244.1.10"]}],
        }

        trace = trace_objects(service, [], [endpoint_slice])
        endpoint = trace.endpoints[0]

        self.assertIsNone(endpoint.ready)
        self.assertTrue(endpoint.effective_ready)
        self.assertTrue(endpoint.effective_serving)
        self.assertFalse(endpoint.effective_terminating)
        self.assertNotIn(
            "one or more endpoints have ready=false", trace.warnings
        )

    def test_endpoint_for_foreign_pod_is_reported(self) -> None:
        service = {
            "metadata": {"name": "web", "namespace": "demo"},
            "spec": {
                "clusterIP": "10.96.0.42",
                "ports": [{"port": 80}],
                "selector": {"app": "web"},
            },
        }
        endpoint_slice = {
            "metadata": {
                "namespace": "demo",
                "labels": {"kubernetes.io/service-name": "web"},
            },
            "endpoints": [
                {
                    "addresses": ["10.244.1.99"],
                    "targetRef": {"name": "old", "uid": "old-uid"},
                    "conditions": {"ready": True},
                }
            ],
        }

        trace = trace_objects(service, [], [endpoint_slice])

        self.assertIn("selector matches no Pods", trace.warnings)
        self.assertIn(
            "EndpointSlice references Pods outside current matches",
            trace.warnings,
        )


if __name__ == "__main__":
    unittest.main()
