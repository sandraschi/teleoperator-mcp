"""teleop_task_dispatch — language goal -> AUTO producer plan.

Turns a natural-language goal into a repeatable AUTO plan for the active
producer. First cut: keyword waypoint profiles (forward, turn, approach,
sweep) consumed by the WaypointProducer; the dispatch only succeeds when the
base group can take AUTO authority (WebXR gate handled by trigger_set_mode).

The VLA branch (goal -> manipulation task on a dual-arm) is registered but
hardware-gated: it requires a platform with a `manip` group and an
out-of-process producer client, which arrives with the wheeled dual-arm.
"""

from __future__ import annotations

import logging
import re

from .config import settings
from .producers.waypoint import Waypoint

logger = logging.getLogger("teleoperator_mcp.tasks")

_WAYPOINT_PATTERNS: dict[str, list[Waypoint]] = {
    "forward": [Waypoint(linear=settings.nav_stub_linear, duration_s=2.0)],
    "reverse": [Waypoint(linear=-settings.nav_stub_linear * 0.5, duration_s=2.0)],
    "turn_left": [Waypoint(linear=0.0, angular=0.5, duration_s=1.0)],
    "turn_right": [Waypoint(linear=0.0, angular=-0.5, duration_s=1.0)],
    "approach": [
        Waypoint(linear=settings.nav_stub_linear * 0.75, duration_s=1.5),
        Waypoint(linear=0.0, duration_s=0.5),
    ],
    "sweep": [
        Waypoint(linear=settings.nav_stub_linear, angular=0.3, duration_s=2.0),
        Waypoint(linear=settings.nav_stub_linear, angular=-0.3, duration_s=2.0),
    ],
}

_KEYWORDS: dict[str, str] = {
    "forward": "forward",
    "straight": "forward",
    "advance": "forward",
    "reverse": "reverse",
    "back up": "reverse",
    "backup": "reverse",
    "back": "reverse",
    "turn left": "turn_left",
    "rotate left": "turn_left",
    "turn right": "turn_right",
    "rotate right": "turn_right",
    "approach": "approach",
    "go to": "approach",
    "sweep": "sweep",
    "scan": "sweep",
    "patrol": "sweep",
}


def _classify(goal: str) -> str | None:
    text = (goal or "").strip().lower()
    if not text:
        return None
    for phrase, profile in _KEYWORDS.items():
        if phrase in text:
            return profile
    if re.search(r"\b(open|grasp|pick|manipulate|fridge|can|handle)\b", text):
        return "vla"
    return None


def build_plan(goal: str) -> list[Waypoint] | None:
    profile = _classify(goal)
    if not profile or profile == "vla":
        return None
    return _WAYPOINT_PATTERNS[profile]


def plan_display(goal: str) -> str | None:
    profile = _classify(goal)
    if profile and profile != "vla":
        return f"nav_waypoint:{profile}"
    if profile == "vla":
        return "vla:manipulation (hardware-gated)"
    return None
