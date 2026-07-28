"""LeRobot parquet export tests."""

from __future__ import annotations

import json
from pathlib import Path

from teleoperator_mcp.recording.export_lerobot import export_lerobot_dataset
from teleoperator_mcp.recording.recorder import SessionRecorder
from teleoperator_mcp.types import BaseCommand, GazeCommand, ProducerCommand


def _seed_episode(base: Path, robot_id: str = "vboomy") -> None:
    rec = SessionRecorder(base)
    rec.start_session(robot_id)
    cmd = ProducerCommand(
        producer_id="human_pose",
        base=BaseCommand(linear=0.2, angular=0.1),
        gaze=GazeCommand(pan=90.0, tilt=85.0),
    )
    rec.log_frame(
        {
            "seq": 1,
            "head": {"yaw": 0.2, "pitch": -0.1, "roll": 0.0},
            "right": {"buttons": {"trigger": 1.0}},
        },
        cmd,
    )
    rec.end_session()


def test_export_writes_parquet_and_meta(tmp_path: Path) -> None:
    _seed_episode(tmp_path)
    out = tmp_path / "lerobot"
    result = export_lerobot_dataset(tmp_path, out, overwrite=True)
    assert result.success is True
    assert result.episodes_exported == 1
    assert result.frames_exported == 1

    parquet = out / "data" / "chunk-000" / "episode_000000.parquet"
    assert parquet.exists()
    info = json.loads((out / "meta" / "info.json").read_text(encoding="utf-8"))
    assert info["total_frames"] == 1
    assert info["codebase_version"] == "v2.1"
    assert info["video_path"] is None


def test_export_skips_empty_episode(tmp_path: Path) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir(parents=True)
    (meta_dir / "episodes.jsonl").write_text(
        json.dumps(
            {"episode_index": 0, "path": "data/episode_000000", "robot_id": "boomy", "length": 0}
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "episode_000000").mkdir(parents=True)
    result = export_lerobot_dataset(tmp_path, tmp_path / "out", overwrite=True)
    assert result.success is False
