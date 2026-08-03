"""Human pose-mapper producer (Mode A direct teleop)."""

from __future__ import annotations

from ..adapters.base import RobotAdapter
from ..adapters.boomy import BoomyAdapter
from ..types import ProducerCommand


class HumanPoseProducer:
    """Maps WebXR pose frames to ProducerCommand for the active robot adapter."""

    producer_id = "human_pose"

    def __init__(self, adapter: RobotAdapter | None = None) -> None:
        self.adapter = adapter or BoomyAdapter()

    def from_pose_frame(
        self,
        head: dict,
        right: dict,
        left: dict | None = None,
        *,
        include_gaze: bool = True,
        hands: dict | None = None,
    ) -> ProducerCommand:
        base = None
        if self.adapter.capabilities.has_base:
            base = self._base_from_controller(right)

        gaze = None
        if include_gaze:
            follow = getattr(self.adapter, "gaze_from_head_follow", None)
            if callable(follow):
                gaze = follow(head)
            else:
                static = getattr(self.adapter, "gaze_from_head", None)
                if callable(static):
                    gaze = static(head)

        manip = self._manip_from_hands(hands, left, right)

        return ProducerCommand(
            producer_id=self.producer_id,
            base=base,  # type: ignore[reportArgumentType]
            gaze=gaze,  # type: ignore[reportArgumentType]
            manip=manip,  # type: ignore[reportArgumentType]
        )

    def _base_from_controller(self, right: dict):
        fn = getattr(self.adapter, "base_from_controller", None)
        if callable(fn):
            return fn(right)
        return None

    def _manip_from_hands(
        self,
        hands: dict | None,
        left: dict | None,
        right: dict | None,
    ) -> dict | None:
        if not self.adapter.capabilities.has_arms:
            return None
        if hands:
            return hands
        # Controller-only fallback: grip triggers as binary grasp hints (phase 1).
        if left or right:
            payload: dict = {"source": "controller_grip"}
            if right:
                payload["right_grip"] = float((right.get("buttons") or {}).get("squeeze", 0.0))
            if left:
                payload["left_grip"] = float((left.get("buttons") or {}).get("squeeze", 0.0))
            if payload.get("right_grip", 0) > 0.5 or payload.get("left_grip", 0) > 0.5:
                return payload
        return None
