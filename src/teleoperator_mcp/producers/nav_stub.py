"""Nav stub AUTO producer — slow forward crawl for Boomy base AUTO tests."""

from __future__ import annotations

import time

from ..types import BaseCommand, ProducerCommand


class NavStubProducer:
    """Placeholder autonomy: constant slow forward until takeover (M3 acceptance stub)."""

    producer_id = "nav_stub"

    def __init__(self, linear: float = 0.12, angular: float = 0.0) -> None:
        self.linear = linear
        self.angular = angular
        self._started_at = time.monotonic()

    def reset_plan(self) -> None:
        """Hand-back to AUTO: replan from current state (fresh timer)."""
        self._started_at = time.monotonic()

    def tick(self) -> ProducerCommand:
        elapsed = time.monotonic() - self._started_at
        # Gentle sweep after 5s to prove switching without Nav2
        ang = self.angular
        lin = self.linear
        if elapsed > 5.0:
            ang = 0.15 if int(elapsed * 2) % 2 == 0 else -0.15
            lin = self.linear * 0.5
        return ProducerCommand(
            producer_id=self.producer_id,
            base=BaseCommand(linear=lin, angular=ang, linear_y=0.0),
            gaze=None,
            manip=None,
        )
