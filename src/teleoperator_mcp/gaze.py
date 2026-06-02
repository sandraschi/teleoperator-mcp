"""Head pose to Boomy PTZ (absolute 0-180° servos)."""

from __future__ import annotations

from .config import settings
from .mappers.boomy import BoomyMapper
from .types import GazeCommand


class GazeFollower:
    """Maps WebXR head euler to absolute pan/tilt with deadband (head-follow prep)."""

    def __init__(self, mapper: BoomyMapper | None = None) -> None:
        self._mapper = mapper or BoomyMapper()
        self._last_pan = settings.ptz_pan_center
        self._last_tilt = settings.ptz_tilt_center

    def reset(self) -> None:
        self.remember(settings.ptz_pan_center, settings.ptz_tilt_center)

    def remember(self, pan: float, tilt: float) -> None:
        self._last_pan = pan
        self._last_tilt = tilt

    def from_head(self, head: dict) -> GazeCommand | None:
        ptz = self._mapper.map_head(head)
        delta = settings.gaze_min_delta_deg
        if abs(ptz.pan - self._last_pan) < delta and abs(ptz.tilt - self._last_tilt) < delta:
            return None
        self._last_pan = ptz.pan
        self._last_tilt = ptz.tilt
        return GazeCommand(pan=ptz.pan, tilt=ptz.tilt)

    @staticmethod
    def absolute(pan: float, tilt: float) -> GazeCommand:
        pan = max(0.0, min(180.0, pan))
        tilt = max(0.0, min(180.0, tilt))
        return GazeCommand(pan=pan, tilt=tilt)

    @staticmethod
    def center() -> GazeCommand:
        return GazeCommand(pan=settings.ptz_pan_center, tilt=settings.ptz_tilt_center)
