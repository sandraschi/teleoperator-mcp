"""Robot adapter registry — ?robot= route selection."""

from __future__ import annotations

from .base import RobotAdapter
from .boomy import BoomyAdapter

PLANNED_ROBOTS: dict[str, dict] = {
    "r1-a5-d": {
        "status": "planned",
        "display_name": "Unitree R1-A5-D (wheeled dual-arm)",
        "message": "Adapter not implemented — hardware-gated (M6).",
    },
}


def list_robots() -> dict[str, dict]:
    boomy = BoomyAdapter().capabilities
    out: dict[str, dict] = {
        "boomy": {
            "status": "available",
            "robot_id": boomy.robot_id,
            "display_name": boomy.display_name,
            "has_base": boomy.has_base,
            "has_arms": boomy.has_arms,
            "hand_type": boomy.hand_type,
        },
    }
    out.update(PLANNED_ROBOTS)
    return out


def create_adapter(robot_id: str) -> RobotAdapter:
    rid = robot_id.strip().lower()
    if rid == "boomy":
        return BoomyAdapter()
    if rid in PLANNED_ROBOTS:
        raise ValueError(f"Robot '{robot_id}' is planned but not available yet")
    raise ValueError(f"Unknown robot '{robot_id}' — supported: boomy")
