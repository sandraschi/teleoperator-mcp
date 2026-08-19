"""Egress sink — tap decoded video frames into teleop episodes.

Closes the T3.3 flywheel gap: a VLA episode without observations is a
half-dataset. The LiveKit publisher decodes each JPEG before capturing it to
the room; we hand that same decoded frame (and the raw JPEG) to this sink,
which keeps a small ring buffer of recent frames keyed by wall-clock time.
The recorder then matches each teleop frame to the nearest video frame within
`TELEOP_LIVEKIT_EGRESS_TOLERANCE_MS`, saves it under the episode's
`images/<key>/` directory (LeRobot v2.1 layout), and records the relative path
as an `observation.image.<key>` column so the parquet export carries it.

Frames that arrive while no teleop session is active are dropped after the
ring buffer overflows — recording is session-scoped by design.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..config import settings

logger = logging.getLogger("teleoperator_mcp.recording.egress")

_RING_MAX = 256  # ~8s @30fps of video frames to match against teleop frames


@dataclass
class VideoFrame:
    captured_at: float  # wall-clock seconds
    jpeg: bytes
    key: str = "observation.image"


@dataclass
class EgressSink:
    """Ring buffer of recently decoded video frames, matched by the recorder."""

    _frames: list[VideoFrame] = field(default_factory=list, repr=False)
    _seq: int = 0

    @property
    def enabled(self) -> bool:
        return settings.livekit_egress_enabled

    def reset(self) -> None:
        """Drop buffered frames (called at teleop session start/end)."""
        self._frames.clear()
        self._seq = 0

    def capture(self, jpeg: bytes, *, key: str = "observation.image") -> None:
        """Feed one decoded frame into the ring buffer (called by the publisher)."""
        if not self.enabled:
            return
        self._seq += 1
        if self._seq % max(1, settings.livekit_egress_interval) != 0:
            return
        self._frames.append(VideoFrame(captured_at=time.time(), jpeg=jpeg, key=key))
        if len(self._frames) > _RING_MAX:
            self._frames.pop(0)

    def nearest(self, teleop_at: float, tolerance_s: float) -> VideoFrame | None:
        """Closest buffered frame to a teleop frame timestamp within tolerance."""
        if not self.enabled or not self._frames:
            return None
        best = min(self._frames, key=lambda f: abs(f.captured_at - teleop_at))
        if abs(best.captured_at - teleop_at) > tolerance_s:
            return None
        return best

    def take(self, teleop_at: float, tolerance_s: float) -> VideoFrame | None:
        """nearest() + remove, so one video frame maps to at most one teleop frame."""
        frame = self.nearest(teleop_at, tolerance_s)
        if frame is not None:
            self._frames.remove(frame)
        return frame

    def status(self) -> dict:
        return {
            "egress_enabled": self.enabled,
            "buffered_frames": len(self._frames),
            "captured_total": self._seq,
            "tolerance_ms": settings.livekit_egress_tolerance_ms,
            "interval": settings.livekit_egress_interval,
        }

    def save_to_episode(
        self,
        frame: VideoFrame,
        episode_dir: Path,
        frame_index: int,
    ) -> str | None:
        """Persist a frame under episode_dir/images/<key>/ and return its LeRobot path.

        Returns a path relative to the recorder root (`data/episode_XXXXXX/images/...`)
        or None when the frame has no JPEG payload. The parquet exporter rewrites the
        `data/episode_` prefix to the chunked layout.
        """
        if not frame.jpeg:
            return None
        images_dir = episode_dir / "images" / frame.key
        images_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{frame_index:06d}.jpg"
        (images_dir / filename).write_bytes(frame.jpeg)
        # Recorder-root-relative path (matches the on-disk JSONL layout).
        return f"{episode_dir.parent.name}/{episode_dir.name}/images/{frame.key}/{filename}"


_sink: EgressSink | None = None


def get_egress() -> EgressSink:
    global _sink
    if _sink is None:
        _sink = EgressSink()
    return _sink
