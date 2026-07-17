#!/usr/bin/env python3
"""Deterministic model of a keyed, rate-limited reconciliation queue.

This is a teaching model, not a compatible reimplementation of client-go.
It demonstrates three properties:

* notifications enqueue keys rather than serialized actions;
* repeated notifications for one key can be coalesced;
* transient failures requeue the key with bounded exponential backoff.
"""

from __future__ import annotations

import argparse
import heapq
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Desired:
    replicas: int
    generation: int


@dataclass(frozen=True, slots=True)
class Observed:
    replicas: int
    observed_generation: int


class KeyedRateLimitedQueue:
    """Small deterministic model of dirty-key coalescing and retry delay."""

    def __init__(self, maximum_backoff: int = 8) -> None:
        self.now = 0
        self.maximum_backoff = maximum_backoff
        self._ready: deque[str] = deque()
        self._ready_keys: set[str] = set()
        self._dirty: set[str] = set()
        self._processing: set[str] = set()
        self._delayed: list[tuple[int, int, str]] = []
        self._scheduled: dict[str, int] = {}
        self._retries: dict[str, int] = {}
        self._sequence = 0

    @property
    def empty(self) -> bool:
        return not self._ready and not self._delayed

    def add(self, key: str) -> None:
        """Mark a key dirty, enqueueing it only when no copy is pending."""
        self._dirty.add(key)
        if (
            key in self._processing
            or key in self._ready_keys
            or key in self._scheduled
        ):
            return
        self._ready.append(key)
        self._ready_keys.add(key)

    def take(self) -> str:
        """Return the next key, advancing logical time to a delayed retry."""
        self._promote_due()
        if not self._ready:
            if not self._delayed:
                raise IndexError("queue is empty")
            self.now = self._delayed[0][0]
            self._promote_due()

        key = self._ready.popleft()
        self._ready_keys.remove(key)
        self._dirty.discard(key)
        self._processing.add(key)
        return key

    def succeed(self, key: str) -> None:
        """Finish successfully and immediately repeat if it became dirty."""
        self._finish(key)
        self._retries.pop(key, None)
        if key in self._dirty and key not in self._ready_keys:
            self._ready.append(key)
            self._ready_keys.add(key)

    def retry(self, key: str) -> int:
        """Finish with an error and schedule a bounded exponential retry."""
        self._finish(key)
        attempt = self._retries.get(key, 0) + 1
        self._retries[key] = attempt
        delay = min(2 ** (attempt - 1), self.maximum_backoff)
        ready_at = self.now + delay
        self._dirty.add(key)
        self._scheduled[key] = ready_at
        self._sequence += 1
        heapq.heappush(self._delayed, (ready_at, self._sequence, key))
        return delay

    def _finish(self, key: str) -> None:
        if key not in self._processing:
            raise ValueError(f"key is not being processed: {key}")
        self._processing.remove(key)

    def _promote_due(self) -> None:
        while self._delayed and self._delayed[0][0] <= self.now:
            ready_at, _, key = heapq.heappop(self._delayed)
            if self._scheduled.get(key) != ready_at:
                continue
            del self._scheduled[key]
            if key not in self._ready_keys and key not in self._processing:
                self._ready.append(key)
                self._ready_keys.add(key)


class FakeStore:
    """Desired and observed state with deterministic injected write failures."""

    def __init__(self) -> None:
        self.desired: dict[str, Desired] = {}
        self.observed: dict[str, Observed] = {}
        self.failures_remaining: dict[str, int] = {}

    def apply(self, key: str, desired: Desired) -> None:
        failures = self.failures_remaining.get(key, 0)
        if failures:
            self.failures_remaining[key] = failures - 1
            raise RuntimeError("transient API write failure")
        self.observed[key] = Observed(
            replicas=desired.replicas,
            observed_generation=desired.generation,
        )


class Reconciler:
    def __init__(self, store: FakeStore, queue: KeyedRateLimitedQueue) -> None:
        self.store = store
        self.queue = queue
        self.trace: list[str] = []

    def run_one(self) -> None:
        key = self.queue.take()
        desired = self.store.desired[key]
        self.trace.append(
            f"t={self.queue.now} reconcile {key}: read generation="
            f"{desired.generation} replicas={desired.replicas}"
        )
        try:
            self.store.apply(key, desired)
        except RuntimeError as error:
            delay = self.queue.retry(key)
            self.trace.append(
                f"t={self.queue.now} {key}: {error}; retry in {delay}"
            )
            return

        self.queue.succeed(key)
        self.trace.append(
            f"t={self.queue.now} {key}: observed generation="
            f"{desired.generation} replicas={desired.replicas}"
        )

    def drain(self) -> None:
        while not self.queue.empty:
            self.run_one()


def demo() -> tuple[list[str], Observed]:
    """Run a scenario with a coalesced update and one transient failure."""
    queue = KeyedRateLimitedQueue()
    store = FakeStore()
    reconciler = Reconciler(store, queue)

    store.desired["web"] = Desired(replicas=3, generation=1)
    queue.add("web")

    # A second notification is coalesced. The worker later reads current state,
    # so generation 1 is never replayed as an instruction.
    store.desired["web"] = Desired(replicas=5, generation=2)
    queue.add("web")

    store.failures_remaining["web"] = 1
    reconciler.drain()
    return reconciler.trace, store.observed["web"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a deterministic reconciliation-queue model."
    )
    parser.add_argument(
        "--assert-final",
        action="store_true",
        help="exit nonzero unless the final observation is generation 2/5 replicas",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trace, observed = demo()
    print("\n".join(trace))
    print(
        "final: "
        f"observed_generation={observed.observed_generation} "
        f"replicas={observed.replicas}"
    )
    if args.assert_final and observed != Observed(5, 2):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

