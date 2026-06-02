"""Human pose-mapper producer (Mode A direct teleop)."""

from __future__ import annotations

from ..adapters.boomy import BoomyAdapter
from ..types import ProducerCommand


class HumanPoseProducer:
    """Maps WebXR pose frames to ProducerCommand for the active robot adapter."""

    producer_id = "human_pose"

    def __init__(self, adapter: BoomyAdapter | None = None) -> None:
        self.adapter = adapter or BoomyAdapter()

    def from_pose_frame(
        self, head: dict, right: dict, *, include_gaze: bool = True
    ) -> ProducerCommand:
        base = BoomyAdapter.base_from_controller(right)
        gaze = BoomyAdapter.gaze_from_head(head) if include_gaze else None
        return ProducerCommand(
            producer_id=self.producer_id,
            base=base,
            gaze=gaze,
            manip=None,
        )
