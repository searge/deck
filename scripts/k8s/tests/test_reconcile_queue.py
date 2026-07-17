from __future__ import annotations

import unittest

from scripts.k8s.reconcile_queue import (
    Desired,
    FakeStore,
    KeyedRateLimitedQueue,
    Observed,
    Reconciler,
    demo,
)


class KeyedRateLimitedQueueTest(unittest.TestCase):
    def test_duplicate_notifications_are_coalesced(self) -> None:
        queue = KeyedRateLimitedQueue()
        queue.add("web")
        queue.add("web")

        self.assertEqual(queue.take(), "web")
        queue.succeed("web")
        self.assertTrue(queue.empty)

    def test_dirty_during_processing_runs_again(self) -> None:
        queue = KeyedRateLimitedQueue()
        queue.add("web")
        self.assertEqual(queue.take(), "web")

        queue.add("web")
        queue.succeed("web")

        self.assertEqual(queue.take(), "web")

    def test_retry_advances_logical_time(self) -> None:
        queue = KeyedRateLimitedQueue()
        queue.add("web")
        self.assertEqual(queue.take(), "web")
        self.assertEqual(queue.retry("web"), 1)

        self.assertEqual(queue.take(), "web")
        self.assertEqual(queue.now, 1)


class ReconcilerTest(unittest.TestCase):
    def test_reconcile_reads_current_state(self) -> None:
        queue = KeyedRateLimitedQueue()
        store = FakeStore()
        reconciler = Reconciler(store, queue)

        store.desired["web"] = Desired(3, 1)
        queue.add("web")
        store.desired["web"] = Desired(5, 2)
        queue.add("web")
        reconciler.drain()

        self.assertEqual(store.observed["web"], Observed(5, 2))
        self.assertNotIn("generation=1", "\n".join(reconciler.trace))

    def test_demo_retries_then_converges(self) -> None:
        trace, observed = demo()

        self.assertEqual(observed, Observed(5, 2))
        self.assertIn("retry in 1", "\n".join(trace))
        self.assertEqual(sum("reconcile web" in line for line in trace), 2)


if __name__ == "__main__":
    unittest.main()

