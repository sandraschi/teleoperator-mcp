# LeRobot / HuggingFace hub export for teleoperator-mcp datasets (T3.3).
# Packs an exported LeRobot dataset directory into a hub-ready layout and
# optionally uploads it. Video/image columns are carried through when present;
# if the dataset has none, upload is refused with a clear message (honesty:
# a VLA episode without observations is a half-dataset).
#
# Usage:
#   uv run python scripts/publish-lerobot-hub.py --input dist/lerobot_export --repo teleop-datasets/boomy-base-2026-08
#   uv run python scripts/publish-lerobot-hub.py --input dist/lerobot_export --repo teleop-datasets/boomy-base-2026-08 --push

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("publish-lerobot-hub")


def _walk_episodes(dataset: Path) -> list[Path]:
    return sorted((dataset / "data").glob("chunk-*/episode_*.parquet"))


def _has_observations(dataset: Path) -> bool:
    """True when any episode parquet has an observation.image/observation.video column."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return False
    for ep in _walk_episodes(dataset):
        try:
            schema = pq.read_schema(ep)
        except Exception:
            continue
        for name in schema.names:
            if name.startswith("observation.image") or name.startswith("observation.video"):
                return True
    return False


def _stage(dataset: Path, staging: Path, repo_name: str) -> None:
    """Copy dataset into a hub-ready repo layout under a temp staging dir."""
    target = staging / repo_name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in ("meta", "data"):
        src = dataset / name
        if src.exists():
            shutil.copytree(src, target / name)
    readme = target / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {repo_name}\n\nTeleoperated dataset from teleoperator-mcp.\n\n"
            "Export via `POST /api/v1/recording/export`; publish via `scripts/publish-lerobot-hub.py`.\n",
            encoding="utf-8",
        )
    logger.info("staged hub repo: %s", target)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish teleoperator-mcp LeRobot dataset to the hub"
    )
    parser.add_argument("--input", required=True, help="Exported LeRobot dataset dir")
    parser.add_argument(
        "--repo", required=True, help="Hub repo id, e.g. teleop-datasets/boomy-base-2026-08"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Upload to the hub (requires huggingface_hub + HF_TOKEN)",
    )
    args = parser.parse_args()

    dataset = Path(args.input)
    if not dataset.is_dir():
        logger.error("dataset dir not found: %s", dataset)
        return 1

    episodes = _walk_episodes(dataset)
    if not episodes:
        logger.error("no episode parquet files under %s/data — run export first", dataset)
        return 1

    if not _has_observations(dataset):
        logger.error(
            "dataset has NO observation.image/video columns (%d episodes). "
            "A VLA episode without observations is a half-dataset; refusing to publish. "
            "Enable LiveKit egress snapshot sync so frames land in the parquet.",
            len(episodes),
        )
        return 1

    staging = Path("dist") / "hub-staging"
    staging.mkdir(parents=True, exist_ok=True)
    _stage(dataset, staging, args.repo)

    if not args.push:
        logger.info("staged %d episodes; add --push to upload to the hub", len(episodes))
        return 0

    try:
        from huggingface_hub import HfApi
    except ImportError:
        logger.error("huggingface_hub not installed: `uv add --dev huggingface_hub`")
        return 1

    api = HfApi()
    api.upload_folder(
        repo_id=args.repo,
        folder_path=str(staging / args.repo),
        repo_type="dataset",
        commit_message="Publish teleoperator-mcp LeRobot dataset",
    )
    logger.info("pushed %s (%d episodes)", args.repo, len(episodes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
