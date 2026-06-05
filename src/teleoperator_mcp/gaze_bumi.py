"""Head pose → Bumi neck (degrees, not PTZ servos)."""

from __future__ import annotations

from .config import settings
from .mappers.bumi import BumiMapper
from .types import GazeCommand


class BumiHeadFollower:
    def __init__(self, mapper: BumiMapper | None = None) -> None:
        self._mapper = mapper or BumiMapper()
        self._last_yaw = 0.0
        self._last_pitch = 0.0

    def remember(self, yaw_deg: float, pitch_deg: float) -> None:
        self._last_yaw = yaw_deg
        self._last_pitch = pitch_deg

    def from_head(self, head: dict) -> GazeCommand | None:
        mapped = self._mapper.map_head(head)
        delta = settings.gaze_min_delta_deg
        if (
            abs(mapped.yaw_deg - self._last_yaw) < delta
            and abs(mapped.pitch_deg - self._last_pitch) < delta
        ):
            return None
        self._last_yaw = mapped.yaw_deg
        self._last_pitch = mapped.pitch_deg
        return GazeCommand(pan=mapped.yaw_deg, tilt=mapped.pitch_deg)
