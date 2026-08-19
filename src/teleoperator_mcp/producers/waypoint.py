"""Waypoint navigation producer for AUTO base authority.

Replaces the forward-only nav stub for dispatched tasks: follow a list of
waypoints (linear/angular set-points with durations). Not a real SLAM/nav
stack — it drives to an implicit goal along a scripted profile, enough to make
`teleop_task_dispatch` meaningful on Boomy and to exercise the arbiter
handoff under a repeatable producer.

Safety: bounded duration, WebXR gate, and the AUTO timer in safety.py still
apply because this producer runs under AUTO authority.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from ..types import BaseCommand, ProducerCommand

logger = logging.getLogger("teleoperator_mcp.producers.waypoint")


@dataclass(frozen=True)
class Waypoint:
    linear: float
    angular: float = 0.0
    duration_s: float = 2.0


class WaypointProducer:
    """AUTO producer that follows a waypoint profile for base drive."""

    producer_id = "nav_waypoint"

    def __init__(self) -> None:
        self._plan: list[Waypoint] = []
        self._started_at: float | None = None
        self._idx = 0

    def dispatch(self, plan: list[Waypoint]) -> None:
        """Start a new waypoint plan (hand-back: replan from current state)."""
        self._plan = list(plan)
        self._idx = 0
        self._started_at = time.monotonic()
        logger.info("waypoint plan dispatched: %s", [w.duration_s for w in self._plan])

    def reset_plan(self) -> None:
        self._plan = []
        self._idx = 0
        self._started_at = None

    def tick(self) -> ProducerCommand:
        if not self._plan or self._started_at is None:
            return ProducerCommand(producer_id=self.producer_id)
        now = time.monotonic()
        while self._idx < len(self._plan):
            wp = self._plan[self._idx]
            seg_end = self._started_at + sum(w.duration_s for w in self._plan[: self._idx + 1])
            if now >= seg_end:
                self._idx += 1
                continue
            return ProducerCommand(
                producer_id=self.producer_id,
                base=BaseCommand(linear=wp.linear, angular=wp.angular, linear_y=0.0),
                gaze=None,
                manip=None,
            )
        # Plan complete -> hold.
        return ProducerCommand(
            producer_id=self.producer_id,
            base=BaseCommand(linear=0.0, angular=0.0, linear_y=0.0),
            gaze=None,
            manip=None,
        )
