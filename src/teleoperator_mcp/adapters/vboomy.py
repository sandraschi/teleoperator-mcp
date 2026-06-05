"""vBoomy virtual twin adapter — Resonite via robotics-mcp OSC."""

from __future__ import annotations

import httpx

from ..config import settings
from ..gaze_bumi import BumiHeadFollower
from ..mappers.vboomy import DriveCommand, HeadCommand, VboomyMapper
from ..types import BaseCommand, GazeCommand, ProducerCommand, RobotCapabilities
from .base import RobotAdapter


class VboomyAdapter(RobotAdapter):
    """Sink for vBoomy: holonomic drive + head in Resonite (training twin for Boomy)."""

    def __init__(self, mapper: VboomyMapper | None = None) -> None:
        self._mapper = mapper or VboomyMapper()
        self._gaze = BumiHeadFollower(self._mapper)  # same deadband pattern, degree output

    @property
    def capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_id="vboomy",
            display_name="vBoomy (Resonite virtual twin)",
            has_base=True,
            has_legs=False,
            balance_risk=False,
            has_arms=False,
            hand_type="none",
            programmable=True,
        )

    @property
    def api_base(self) -> str:
        return settings.robotics_api_url.rstrip("/")

    async def apply_gaze(self, gaze: GazeCommand, client: httpx.AsyncClient) -> bool:
        cmd = HeadCommand(yaw_deg=gaze.pan, pitch_deg=gaze.tilt)
        ok = await self._mapper.apply_head(cmd, client)
        if ok:
            self._gaze.remember(gaze.pan, gaze.tilt)
        return ok

    async def apply(self, command: ProducerCommand, client: httpx.AsyncClient) -> None:
        if command.base is not None:
            drive = DriveCommand(linear=command.base.linear, angular=command.base.angular)
            await self._mapper.apply_drive(drive, client)
        if command.gaze is not None:
            await self.apply_gaze(command.gaze, client)

    async def e_stop(self, client: httpx.AsyncClient) -> None:
        await self._mapper.e_stop(client)

    @staticmethod
    def gaze_from_head(head: dict) -> GazeCommand:
        mapped = VboomyMapper().map_head(head)
        return GazeCommand(pan=mapped.yaw_deg, tilt=mapped.pitch_deg)

    def gaze_from_head_follow(self, head: dict) -> GazeCommand | None:
        return self._gaze.from_head(head)

    @staticmethod
    def base_from_controller(right: dict) -> BaseCommand:
        drive = VboomyMapper().map_drive(right)
        return BaseCommand(linear=drive.linear, angular=drive.angular, linear_y=0.0)
