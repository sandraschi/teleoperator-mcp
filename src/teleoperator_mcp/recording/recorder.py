"""Teleop session recording — LeRobot-compatible JSONL episodes (M4)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import settings
from ..types import ProducerCommand

logger = logging.getLogger("teleoperator_mcp.recording")

_recorder: SessionRecorder | None = None


@dataclass
class RecordingState:
    active: bool = False
    session_id: str | None = None
    robot_id: str | None = None
    started_at: float | None = None
    frame_count: int = 0
    episode_dir: str | None = None


@dataclass
class SessionRecorder:
    """Append-only frame log; finalize writes meta for LeRobot export."""

    base_dir: Path
    state: RecordingState = field(default_factory=RecordingState)
    _frames: list[dict[str, Any]] = field(default_factory=list, repr=False)
    _episode_index: int = 0

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._episode_index = self._next_episode_index()

    def _next_episode_index(self) -> int:
        meta = self.base_dir / "meta" / "episodes.jsonl"
        if not meta.exists():
            return 0
        count = 0
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.strip():
                count += 1
        return count

    def status(self) -> dict[str, Any]:
        return {
            "recording_enabled": settings.recording_enabled,
            "recording_dir": str(self.base_dir),
            "active": self.state.active,
            "session_id": self.state.session_id,
            "robot_id": self.state.robot_id,
            "frame_count": self.state.frame_count,
            "episode_dir": self.state.episode_dir,
        }

    def start_session(self, robot_id: str, *, client: str | None = None) -> str | None:
        if not settings.recording_enabled:
            return None
        self.end_session()
        session_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        ep_idx = self._episode_index
        episode_dir = self.base_dir / "data" / f"episode_{ep_idx:06d}"
        episode_dir.mkdir(parents=True, exist_ok=True)
        self._frames = []
        self.state = RecordingState(
            active=True,
            session_id=session_id,
            robot_id=robot_id,
            started_at=time.time(),
            frame_count=0,
            episode_dir=str(episode_dir),
        )
        (episode_dir / "session.json").write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "robot_id": robot_id,
                    "client": client,
                    "started_at": session_id,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("recording started session=%s robot=%s", session_id, robot_id)
        return session_id

    def log_frame(
        self,
        payload: dict[str, Any],
        command: ProducerCommand,
        *,
        sources: dict[str, str] | None = None,
        authority: dict[str, Any] | None = None,
    ) -> None:
        if not self.state.active:
            return
        msg_type = payload.get("type")
        if msg_type in ("heartbeat", "estop", "takeover"):
            return

        base = command.base
        gaze = command.gaze
        action = [
            float(base.linear if base else 0.0),
            float(base.angular if base else 0.0),
            float(base.linear_y if base else 0.0),
            float(gaze.pan if gaze else settings.ptz_pan_center),
            float(gaze.tilt if gaze else settings.ptz_tilt_center),
        ]
        head = payload.get("head") or {}
        right = payload.get("right") or {}

        row = {
            "frame_index": self.state.frame_count,
            "timestamp": time.time(),
            "seq": payload.get("seq"),
            "observation.state": action,
            "action": action,
            "observation.head.yaw": float(head.get("yaw", 0.0)),
            "observation.head.pitch": float(head.get("pitch", 0.0)),
            "observation.head.roll": float(head.get("roll", 0.0)),
            "observation.controller.trigger": float(
                (right.get("buttons") or {}).get("trigger", 0.0)
            ),
            "observation.controller.axes": list(right.get("axes") or []),
            "producer_id": command.producer_id,
            "authority": authority,
            "sources": sources,
        }
        self._frames.append(row)
        self.state.frame_count += 1

    def end_session(self) -> dict[str, Any] | None:
        if not self.state.active:
            return None

        episode_dir = Path(self.state.episode_dir) if self.state.episode_dir else None
        frame_count = self.state.frame_count
        session_id = self.state.session_id
        robot_id = self.state.robot_id
        ep_idx = self._episode_index

        summary: dict[str, Any] = {
            "session_id": session_id,
            "robot_id": robot_id,
            "frame_count": frame_count,
            "duration_s": round(time.time() - (self.state.started_at or time.time()), 3),
            "episode_index": ep_idx,
        }

        if episode_dir and self._frames:
            frames_path = episode_dir / "frames.jsonl"
            with frames_path.open("w", encoding="utf-8") as fh:
                for row in self._frames:
                    fh.write(json.dumps(row) + "\n")
            summary_path = episode_dir / "summary.json"
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            self._append_episode_meta(ep_idx, session_id, robot_id, frame_count, episode_dir)

        self._ensure_info_json(robot_id)
        self._frames = []
        self.state = RecordingState()
        self._episode_index = ep_idx + 1
        logger.info("recording ended session=%s frames=%s", session_id, frame_count)
        return summary

    def _meta_dir(self) -> Path:
        d = self.base_dir / "meta"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _append_episode_meta(
        self,
        episode_index: int,
        session_id: str | None,
        robot_id: str | None,
        length: int,
        episode_dir: Path,
    ) -> None:
        meta_path = self._meta_dir() / "episodes.jsonl"
        entry = {
            "episode_index": episode_index,
            "session_id": session_id,
            "robot_id": robot_id,
            "length": length,
            "task": "teleop_base_gaze",
            "path": str(episode_dir.relative_to(self.base_dir)).replace("\\", "/"),
        }
        with meta_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def _ensure_info_json(self, robot_id: str | None) -> None:
        info_path = self._meta_dir() / "info.json"
        if info_path.exists():
            return
        info = {
            "codebase_version": "v2.1",
            "robot_type": robot_id or "boomy",
            "fps": settings.recording_fps,
            "features": {
                "observation.state": {"dtype": "float32", "shape": [5]},
                "action": {"dtype": "float32", "shape": [5]},
                "observation.head.yaw": {"dtype": "float32", "shape": [1]},
                "observation.head.pitch": {"dtype": "float32", "shape": [1]},
            },
            "note": "JSONL episodes; export: scripts/export-lerobot.ps1 or POST /api/v1/recording/export",
        }
        info_path.write_text(json.dumps(info, indent=2), encoding="utf-8")


def get_recorder() -> SessionRecorder:
    global _recorder
    if _recorder is None:
        _recorder = SessionRecorder(Path(settings.recording_dir))
    return _recorder
