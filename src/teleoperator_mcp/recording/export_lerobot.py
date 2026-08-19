"""Export teleop JSONL episodes to LeRobot v2.1-style parquet dataset."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("teleoperator_mcp.recording.export_lerobot")

DEFAULT_TASK = "teleop_base_gaze"
FEATURES: dict[str, dict[str, Any]] = {
    "observation.state": {
        "dtype": "float32",
        "shape": [5],
        "names": ["linear", "angular", "linear_y", "pan", "tilt"],
    },
    "action": {
        "dtype": "float32",
        "shape": [5],
        "names": ["linear", "angular", "linear_y", "pan", "tilt"],
    },
    "observation.head.yaw": {"dtype": "float32", "shape": [1], "names": None},
    "observation.head.pitch": {"dtype": "float32", "shape": [1], "names": None},
    "observation.head.roll": {"dtype": "float32", "shape": [1], "names": None},
    "observation.controller.trigger": {"dtype": "float32", "shape": [1], "names": None},
}


@dataclass
class ExportResult:
    success: bool
    message: str
    input_dir: str
    output_dir: str
    episodes_exported: int = 0
    frames_exported: int = 0
    parquet_files: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _read_episodes_meta(base_dir: Path) -> list[dict[str, Any]]:
    meta_path = base_dir / "meta" / "episodes.jsonl"
    if not meta_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in meta_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_frames(episode_dir: Path) -> list[dict[str, Any]]:
    frames_path = episode_dir / "frames.jsonl"
    if not frames_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in frames_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _image_path_rewrite(value: str) -> str:
    """Rewrite a recorder-root image path to the chunked dataset layout.

    Recorder writes:        data/episode_000000/images/<key>/000000.jpg
    Dataset writes:         data/chunk-000/episode_000000/images/<key>/000000.jpg
    """
    text = str(value).replace("\\", "/")
    stripped = text[5:] if text.startswith("data/") else text
    return f"data/chunk-000/{stripped}"


def _episode_to_table_rows(
    frames: list[dict[str, Any]],
    *,
    episode_index: int,
    task_index: int,
    global_index_start: int,
    fps: int,
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    global_index = global_index_start
    for frame in frames:
        obs_state = [float(x) for x in (frame.get("observation.state") or [0.0] * 5)]
        action = [float(x) for x in (frame.get("action") or obs_state)]
        while len(obs_state) < 5:
            obs_state.append(0.0)
        while len(action) < 5:
            action.append(0.0)
        ts = float(frame.get("timestamp", 0.0))
        fi = int(frame.get("frame_index", len(rows)))
        row: dict[str, Any] = {
            "timestamp": ts,
            "frame_index": fi,
            "episode_index": episode_index,
            "index": global_index,
            "task_index": task_index,
            "observation.state": obs_state[:5],
            "action": action[:5],
            "observation.head.yaw": float(frame.get("observation.head.yaw", 0.0)),
            "observation.head.pitch": float(frame.get("observation.head.pitch", 0.0)),
            "observation.head.roll": float(frame.get("observation.head.roll", 0.0)),
            "observation.controller.trigger": float(
                frame.get("observation.controller.trigger", 0.0)
            ),
            "next.done": fi >= len(frames) - 1,
        }
        # Carry any egress image columns into the dataset (chunked path).
        for key, value in frame.items():
            if key.startswith("observation.image.") and isinstance(value, str):
                row[key] = _image_path_rewrite(value)
        rows.append(row)
        global_index += 1
    return rows, global_index


def _write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("cannot write empty episode")

    fields: list[pa.Field] = [
        ("timestamp", pa.float64()),
        ("frame_index", pa.int64()),
        ("episode_index", pa.int64()),
        ("index", pa.int64()),
        ("task_index", pa.int64()),
        ("observation.state", pa.list_(pa.float32(), 5)),
        ("action", pa.list_(pa.float32(), 5)),
        ("observation.head.yaw", pa.float32()),
        ("observation.head.pitch", pa.float32()),
        ("observation.head.roll", pa.float32()),
        ("observation.controller.trigger", pa.float32()),
        ("next.done", pa.bool_()),
    ]
    # Dynamic egress image columns: observation.image.<key> -> string (dataset-relative path).
    image_cols = sorted({k for r in rows for k in r if k.startswith("observation.image.")})
    fields.extend((name, pa.string()) for name in image_cols)

    table = pa.Table.from_pylist(rows, schema=pa.schema(fields))
    pq.write_table(table, path, compression="snappy")


def _write_meta(
    output_dir: Path,
    *,
    episodes: list[dict[str, Any]],
    total_frames: int,
    fps: int,
    robot_type: str,
    has_images: bool = False,
) -> None:
    meta_dir = output_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    tasks_path = meta_dir / "tasks.jsonl"
    if not tasks_path.exists():
        tasks_path.write_text(
            json.dumps({"task_index": 0, "task": DEFAULT_TASK}) + "\n",
            encoding="utf-8",
        )

    features = dict(FEATURES)
    if has_images:
        features["observation.image.image"] = {"dtype": "image", "shape": [1, 1, 3]}
    info = {
        "codebase_version": "v2.1",
        "robot_type": robot_type,
        "fps": fps,
        "features": features,
        "total_episodes": len(episodes),
        "total_frames": total_frames,
        "total_tasks": 1,
        "chunks_size": 1000,
        "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
        "video_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}/images/observation.image"
        if has_images
        else None,
        "exported_at": datetime.now(UTC).isoformat(),
        "source": "teleoperator-mcp JSONL",
        "note": (
            "Egress image frames recorded via the LiveKit egress sink (observation.image.*)."
            if has_images
            else "No image columns — enable TELEOP_LIVEKIT_EGRESS_ENABLED to capture video frames."
        ),
    }
    (meta_dir / "info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    episodes_out = meta_dir / "episodes.jsonl"
    with episodes_out.open("w", encoding="utf-8") as fh:
        for ep in episodes:
            fh.write(json.dumps(ep) + "\n")


def export_lerobot_dataset(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    episode_indices: list[int] | None = None,
    fps: int = 30,
    overwrite: bool = False,
) -> ExportResult:
    """Convert JSONL teleop recordings to LeRobot-compatible parquet episodes."""
    src = Path(input_dir)
    dst = Path(output_dir)

    if not src.exists():
        return ExportResult(False, f"input dir not found: {src}", str(src), str(dst))

    meta_episodes = _read_episodes_meta(src)
    if not meta_episodes:
        return ExportResult(False, "no episodes in meta/episodes.jsonl", str(src), str(dst))

    if dst.exists() and overwrite:
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    info_path = src / "meta" / "info.json"
    robot_type = "teleop"
    if info_path.exists():
        try:
            robot_type = json.loads(info_path.read_text(encoding="utf-8")).get(
                "robot_type", robot_type
            )
        except json.JSONDecodeError:
            pass

    selected = meta_episodes
    if episode_indices is not None:
        wanted = set(episode_indices)
        selected = [ep for ep in meta_episodes if int(ep.get("episode_index", -1)) in wanted]

    parquet_files: list[str] = []
    skipped: list[str] = []
    exported_meta: list[dict[str, Any]] = []
    total_frames = 0
    global_index = 0

    chunk_dir = dst / "data" / "chunk-000"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    for ep in selected:
        ep_idx = int(ep.get("episode_index", len(exported_meta)))
        rel_path = ep.get("path") or f"data/episode_{ep_idx:06d}"
        episode_dir = src / rel_path
        frames = _load_frames(episode_dir)
        if not frames:
            skipped.append(f"episode_{ep_idx:06d} (no frames)")
            continue

        rows, global_index = _episode_to_table_rows(
            frames,
            episode_index=ep_idx,
            task_index=0,
            global_index_start=global_index,
            fps=fps,
        )
        parquet_name = f"episode_{ep_idx:06d}.parquet"
        parquet_path = chunk_dir / parquet_name
        _write_parquet(parquet_path, rows)

        # Copy egress images into the chunked layout next to the parquet.
        src_images = episode_dir / "images"
        if src_images.exists():
            dst_images = chunk_dir / f"episode_{ep_idx:06d}" / "images"
            shutil.copytree(src_images, dst_images, dirs_exist_ok=True)

        rel_parquet = str(parquet_path.relative_to(dst)).replace("\\", "/")
        parquet_files.append(rel_parquet)
        total_frames += len(rows)
        exported_meta.append(
            {
                "episode_index": ep_idx,
                "session_id": ep.get("session_id"),
                "robot_id": ep.get("robot_id"),
                "length": len(rows),
                "task": ep.get("task", DEFAULT_TASK),
                "task_index": 0,
                "path": rel_parquet,
            }
        )

    if not exported_meta:
        return ExportResult(
            False,
            "no episodes exported (all empty or missing frames)",
            str(src),
            str(dst),
            skipped=skipped,
        )

    has_images = any(
        (
            episode_dir := src
            / (ep.get("path") or f"data/episode_{int(ep.get('episode_index', 0)):06d}")
        ).exists()
        and (episode_dir / "images").exists()
        for ep in selected
    )

    _write_meta(
        dst,
        episodes=exported_meta,
        total_frames=total_frames,
        fps=fps,
        robot_type=robot_type,
        has_images=has_images,
    )

    msg = f"exported {len(exported_meta)} episode(s), {total_frames} frame(s) → {dst}"
    logger.info(msg)
    return ExportResult(
        True,
        msg,
        str(src),
        str(dst),
        episodes_exported=len(exported_meta),
        frames_exported=total_frames,
        parquet_files=parquet_files,
        skipped=skipped,
    )


def export_summary(result: ExportResult) -> dict[str, Any]:
    return {
        "success": result.success,
        "message": result.message,
        "input_dir": result.input_dir,
        "output_dir": result.output_dir,
        "episodes_exported": result.episodes_exported,
        "frames_exported": result.frames_exported,
        "parquet_files": result.parquet_files,
        "skipped": result.skipped,
        "lerobot_train_hint": (
            "pip install lerobot && lerobot-train "
            f"--dataset.repo_id=local/teleop --dataset.root={result.output_dir}"
            if result.success
            else None
        ),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Export teleop JSONL to LeRobot parquet")
    parser.add_argument("--input", default="data/teleop_recordings", help="JSONL recording root")
    parser.add_argument("--output", default="data/lerobot_export", help="Parquet output root")
    parser.add_argument(
        "--episodes", default="", help="Comma-separated episode indices (default: all)"
    )
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    indices: list[int] | None = None
    if args.episodes.strip():
        indices = [int(x.strip()) for x in args.episodes.split(",") if x.strip()]

    result = export_lerobot_dataset(
        args.input,
        args.output,
        episode_indices=indices,
        fps=args.fps,
        overwrite=args.overwrite,
    )
    raise SystemExit(0 if result.success else 1)


if __name__ == "__main__":
    main()
