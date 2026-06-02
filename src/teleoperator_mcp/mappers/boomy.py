"""Boomy (Yahboom Raspbot v2) teleop mapper - head -> PTZ, stick -> cmd_vel."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from ..config import settings

logger = logging.getLogger("teleoperator_mcp.mappers.boomy")


@dataclass
class DriveCommand:
    linear: float = 0.0
    angular: float = 0.0
    linear_y: float = 0.0


@dataclass
class PtzCommand:
    pan: float = 0.0
    tilt: float = 0.0


class BoomyMapper:
    """Maps WebXR pose frames to yahboom-mcp REST calls."""

    @property
    def api_base(self) -> str:
        return settings.yahboom_api_url.rstrip("/")

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def map_head(self, head: dict) -> PtzCommand:
        yaw = float(head.get("yaw", 0.0))
        pitch = float(head.get("pitch", 0.0))
        pan_offset = self._clamp(yaw * settings.pan_gain, -90.0, 90.0)
        tilt_offset = self._clamp(pitch * settings.tilt_gain, -45.0, 45.0)
        pan = self._clamp(settings.ptz_pan_center + pan_offset, 0.0, 180.0)
        tilt = self._clamp(settings.ptz_tilt_center + tilt_offset, 0.0, 180.0)
        return PtzCommand(pan=pan, tilt=tilt)

    def map_drive(self, right: dict) -> DriveCommand:
        buttons = right.get("buttons") or {}
        trigger = float(buttons.get("trigger", 0.0))
        if trigger <= 0.5:
            return DriveCommand()
        axes = right.get("axes") or [0.0, 0.0]
        stick_x = float(axes[0]) if len(axes) > 0 else 0.0
        stick_y = float(axes[1]) if len(axes) > 1 else 0.0
        return DriveCommand(
            linear=-stick_y * settings.max_linear,
            angular=-stick_x * settings.max_angular,
        )

    async def apply_drive(self, cmd: DriveCommand, client: httpx.AsyncClient) -> bool:
        url = f"{self.api_base}/api/v1/control/move"
        params = {"linear": cmd.linear, "angular": cmd.angular, "linear_y": cmd.linear_y}
        try:
            resp = await client.post(url, params=params, timeout=2.0)
            return resp.is_success
        except httpx.HTTPError as exc:
            logger.warning("drive command failed: %s", exc)
            return False

    async def apply_ptz(self, cmd: PtzCommand, client: httpx.AsyncClient) -> bool:
        url = f"{self.api_base}/api/v1/control/tool"
        body = {
            "operation": "camera_set_pos",
            "param1": int(cmd.pan),
            "param2": int(cmd.tilt),
        }
        try:
            resp = await client.post(url, json=body, timeout=2.0)
            return resp.is_success
        except httpx.HTTPError as exc:
            logger.warning("ptz command failed: %s", exc)
            return False

    async def e_stop(self, client: httpx.AsyncClient) -> None:
        await self.apply_drive(DriveCommand(), client)
