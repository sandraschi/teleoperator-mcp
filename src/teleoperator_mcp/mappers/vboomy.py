"""vBoomy (Resonite virtual twin) teleop mapper — REST to robotics-mcp OSC gateway."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from ..config import settings

logger = logging.getLogger("teleoperator_mcp.mappers.vboomy")


@dataclass
class DriveCommand:
    linear: float = 0.0
    angular: float = 0.0


@dataclass
class HeadCommand:
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0


class VboomyMapper:
    """Maps WebXR pose frames to robotics-mcp virtual robot control API."""

    @property
    def api_base(self) -> str:
        return settings.robotics_api_url.rstrip("/")

    @property
    def robot_id(self) -> str:
        return settings.vboomy_robot_id

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def map_head(self, head: dict) -> HeadCommand:
        yaw = float(head.get("yaw", 0.0))
        pitch = float(head.get("pitch", 0.0))
        return HeadCommand(
            yaw_deg=self._clamp(yaw * settings.pan_gain, -90.0, 90.0),
            pitch_deg=self._clamp(pitch * settings.tilt_gain, -45.0, 45.0),
        )

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

    async def _control(self, client: httpx.AsyncClient, body: dict) -> bool:
        url = f"{self.api_base}/api/v1/robots/{self.robot_id}/control"
        try:
            resp = await client.post(url, json=body, timeout=2.0)
            if resp.is_success:
                return True
            logger.warning("vboomy control HTTP %s: %s", resp.status_code, resp.text[:200])
            return False
        except httpx.HTTPError as exc:
            logger.warning("vboomy control failed: %s", exc)
            return False

    async def apply_drive(self, cmd: DriveCommand, client: httpx.AsyncClient) -> bool:
        return await self._control(
            client,
            {"action": "move", "linear": cmd.linear, "angular": cmd.angular},
        )

    async def apply_head(self, cmd: HeadCommand, client: httpx.AsyncClient) -> bool:
        return await self._control(
            client,
            {"action": "head", "yaw": cmd.yaw_deg, "pitch": cmd.pitch_deg},
        )

    async def e_stop(self, client: httpx.AsyncClient) -> None:
        await self._control(client, {"action": "emergency_stop"})
