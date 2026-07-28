"""Shared runtime — robot binding, arbiter, recording."""

from __future__ import annotations

from .adapters.base import RobotAdapter
from .adapters.registry import create_adapter, list_robots
from .arbiter.core import AuthorityArbiter
from .producers.human_pose import HumanPoseProducer

_active_robot: str = "boomy"
_adapter: RobotAdapter = create_adapter("boomy")
_human = HumanPoseProducer(_adapter)  # type: ignore[arg-type]
_arbiter = AuthorityArbiter(_adapter, human=_human)  # type: ignore[arg-type]


def bind_robot(robot_id: str) -> RobotAdapter:
    """Select adapter for WS ?robot= (M2). Rebuilds arbiter + human producer."""
    global _active_robot, _adapter, _human, _arbiter
    _adapter = create_adapter(robot_id)
    _human = HumanPoseProducer(_adapter)  # type: ignore[arg-type]
    _arbiter = AuthorityArbiter(_adapter, human=_human)  # type: ignore[arg-type]
    _active_robot = robot_id.lower()
    return _adapter


def get_adapter() -> RobotAdapter:
    return _adapter


def get_arbiter() -> AuthorityArbiter:
    return _arbiter


def get_active_robot() -> str:
    return _active_robot


def robots_catalog() -> dict[str, dict]:
    return list_robots()
