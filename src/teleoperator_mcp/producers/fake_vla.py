"""Fake VLA producer — deterministic simulation of an out-of-process VLA.

Purpose (T2.1): exercise the arbiter's producer contract, AUTO authority, and
bumpless handoff WITHOUT a real policy or hardware. It emits scripted manip
and/or base commands at a fixed cadence with a declared confidence, so tests
can assert:

- the arbiter routes AUTO groups to the fake producer,
- takeover seeds the human command from the producer's current output (no
  lurch at the switch),
- confidence-blended SHARED output is bounded and monotone.

The real WALL-OSS / UnifoLM producers are out-of-process clients speaking the
same ProducerCommand schema; this fake is the in-process stand-in for tests.
"""

from __future__ import annotations

import time

from ..config import settings
from ..types import BaseCommand, ProducerCommand


class FakeVlaProducer:
    producer_id = "vla"

    def __init__(
        self,
        *,
        linear: float | None = None,
        angular: float | None = None,
        confidence: float = 0.8,
        emits_manip: bool = True,
    ) -> None:
        self.linear = settings.nav_stub_linear if linear is None else linear
        self.angular = settings.nav_stub_angular if angular is None else angular
        self.confidence = confidence
        self.emits_manip = emits_manip
        self._started_at: float | None = None
        self._steps = 0

    def reset_plan(self) -> None:
        """Hand-back: replan from current state (stateless for the fake)."""
        self._started_at = time.monotonic()
        self._steps = 0

    def tick(self) -> ProducerCommand:
        if self._started_at is None:
            self._started_at = time.monotonic()
        self._steps += 1
        cmd = ProducerCommand(
            producer_id=self.producer_id,
            base=BaseCommand(linear=self.linear, angular=self.angular, linear_y=0.0),
            gaze=None,
            confidence=self.confidence,
        )
        if self.emits_manip:
            cmd.manip = {
                "source": "fake_vla",
                "step": self._steps,
                "grasp": 0.5 + 0.1 * ((self._steps % 10) / 10.0),
            }
        return cmd

    def current_command(self) -> ProducerCommand:
        """Current output without advancing — used to seed human takeover."""
        return self.tick()

    @property
    def steps(self) -> int:
        return self._steps
