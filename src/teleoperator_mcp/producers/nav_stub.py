"""Nav stub AUTO producer — slow forward crawl for Boomy base AUTO tests."""

from __future__ import annotations

from ..config import settings
from ..types import BaseCommand, ProducerCommand


class NavStubProducer:
    """Placeholder autonomy: constant slow forward only (no turns — furniture safety)."""

    producer_id = "nav_stub"

    def __init__(self, linear: float | None = None, angular: float | None = None) -> None:
        self.linear = settings.nav_stub_linear if linear is None else linear
        self.angular = settings.nav_stub_angular if angular is None else angular

    def reset_plan(self) -> None:
        """Hand-back to AUTO: replan from current state (no-op for forward-only stub)."""
        return

    def tick(self) -> ProducerCommand:
        return ProducerCommand(
            producer_id=self.producer_id,
            base=BaseCommand(linear=self.linear, angular=self.angular, linear_y=0.0),
            gaze=None,
            manip=None,
        )
