"""Bumi (Noetix humanoid) teleop mapper — head → neck, stick → gated walk."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from ..config import settings

logger = logging.getLogger("teleoperator_mcp.mappers.bumi")


@dataclass
class WalkCommand:
    linear: float = 0.0
    angular: float = 0.0


@dataclass
class HeadCommand:
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0


class BumiMapper:
    """Maps WebXR pose frames to bumi-mcp REST (/api/v1)."""

    @property
    def api_base(self) -> str:
        return settings.bumi_api_url.rstrip("/")

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def map_head(self, head: dict) -> HeadCommand:
        yaw = float(head.get("yaw", 0.0))
        pitch = float(head.get("pitch", 0.0))
        yaw_deg = self._clamp(yaw * settings.bumi_head_yaw_gain, -90.0, 90.0)
        pitch_deg = self._clamp(pitch * settings.bumi_head_pitch_gain, -45.0, 45.0)
        return HeadCommand(yaw_deg=yaw_deg, pitch_deg=pitch_deg)

    def map_walk(self, right: dict) -> WalkCommand:
        buttons = right.get("buttons") or {}
        trigger = float(buttons.get("trigger", 0.0))
        if trigger <= 0.5:
            return WalkCommand()
        axes = right.get("axes") or [0.0, 0.0]
        stick_x = float(axes[0]) if len(axes) > 0 else 0.0
        stick_y = float(axes[1]) if len(axes) > 1 else 0.0
        return WalkCommand(
            linear=-stick_y * settings.bumi_max_linear,
            angular=-stick_x * settings.bumi_max_angular,
        )

    async def apply_walk(self, cmd: WalkCommand, client: httpx.AsyncClient) -> bool:
        url = f"{self.api_base}/api/v1/control/walk"
        params = {"linear": cmd.linear, "angular": cmd.angular}
        try:
            resp = await client.post(url, params=params, timeout=2.0)
            return resp.is_success
        except httpx.HTTPError as exc:
            logger.warning("walk command failed: %s", exc)
            return False

    async def apply_head(self, cmd: HeadCommand, client: httpx.AsyncClient) -> bool:
        url = f"{self.api_base}/api/v1/control/head"
        params = {"yaw": cmd.yaw_deg, "pitch": cmd.pitch_deg}
        try:
            resp = await client.post(url, params=params, timeout=2.0)
            return resp.is_success
        except httpx.HTTPError as exc:
            logger.warning("head command failed: %s", exc)
            return False

    async def apply_manip(self, manip: dict, client: httpx.AsyncClient) -> bool:
        url = f"{self.api_base}/api/v1/control/manip"
        try:
            resp = await client.post(url, json=manip, timeout=2.0)
            return resp.is_success
        except httpx.HTTPError as exc:
            logger.warning("manip command failed: %s", exc)
            return False

    async def e_stop(self, client: httpx.AsyncClient) -> None:
        url = f"{self.api_base}/api/v1/control/estop"
        try:
            await client.post(url, timeout=2.0)
        except httpx.HTTPError as exc:
            logger.warning("estop failed: %s", exc)
