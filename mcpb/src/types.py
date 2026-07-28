"""Shared command and capability types for producers and adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HandType = Literal["none", "gripper", "dexterous"]


@dataclass
class BaseCommand:
    linear: float = 0.0
    angular: float = 0.0
    linear_y: float = 0.0


@dataclass
class GazeCommand:
    pan: float = 0.0
    tilt: float = 0.0


@dataclass
class ProducerCommand:
    """Partial command keyed by actuator group (see DUAL_MODE_ARCHITECTURE.md)."""

    producer_id: str
    base: BaseCommand | None = None
    gaze: GazeCommand | None = None
    manip: dict | None = None
    confidence: float | None = None


@dataclass
class RobotCapabilities:
    has_base: bool = True
    has_legs: bool = False
    balance_risk: bool = False
    has_arms: bool = False
    hand_type: HandType = "none"
    programmable: bool = True
    robot_id: str = "unknown"
    display_name: str = "Robot"


@dataclass
class ActuatorGroups:
    """Which groups a platform exposes to the arbiter (M3)."""

    base: bool = False
    manip: bool = False
    gaze: bool = False


def groups_from_capabilities(cap: RobotCapabilities) -> ActuatorGroups:
    return ActuatorGroups(
        base=cap.has_base,
        manip=cap.has_arms,
        gaze=cap.has_base or cap.has_arms,  # PTZ/head on most platforms
    )
