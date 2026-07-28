"""Yahboom Raspbot v2 (Boomy) robot adapter via yahboom-mcp REST."""

from __future__ import annotations

import httpx

from ..config import settings
from ..gaze import GazeFollower
from ..mappers.boomy import BoomyMapper, DriveCommand, PtzCommand
from ..types import BaseCommand, GazeCommand, ProducerCommand, RobotCapabilities
from .base import RobotAdapter


class BoomyAdapter(RobotAdapter):
    """Sink for Boomy: base (cmd_vel) + gaze (PTZ). No manip group."""

    def __init__(self, mapper: BoomyMapper | None = None) -> None:
        self._mapper = mapper or BoomyMapper()
        self._gaze = GazeFollower(self._mapper)

    @property
    def gaze_follower(self) -> GazeFollower:
        return self._gaze

    async def apply_gaze(self, gaze: GazeCommand, client: httpx.AsyncClient) -> bool:
        ptz = PtzCommand(pan=gaze.pan, tilt=gaze.tilt)
        ok = await self._mapper.apply_ptz(ptz, client)
        if ok:
            self._gaze.remember(gaze.pan, gaze.tilt)
        return ok

    @property
    def capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_id="boomy",
            display_name="Yahboom Raspbot v2 (Boomy)",
            has_base=True,
            has_legs=False,
            balance_risk=False,
            has_arms=False,
            hand_type="none",
            programmable=True,
        )

    @property
    def api_base(self) -> str:
        return settings.yahboom_api_url.rstrip("/")

    async def apply(self, command: ProducerCommand, client: httpx.AsyncClient) -> None:
        if command.base is not None:
            drive = DriveCommand(
                linear=command.base.linear,
                angular=command.base.angular,
                linear_y=command.base.linear_y,
            )
            await self._mapper.apply_drive(drive, client)
        if command.gaze is not None:
            await self.apply_gaze(command.gaze, client)

    async def e_stop(self, client: httpx.AsyncClient) -> None:
        await self._mapper.e_stop(client)

    @staticmethod
    def gaze_from_head(head: dict) -> GazeCommand:
        ptz = BoomyMapper().map_head(head)
        return GazeCommand(pan=ptz.pan, tilt=ptz.tilt)

    def gaze_from_head_follow(self, head: dict) -> GazeCommand | None:
        return self._gaze.from_head(head)

    @staticmethod
    def base_from_controller(right: dict) -> BaseCommand:
        drive = BoomyMapper().map_drive(right)
        return BaseCommand(linear=drive.linear, angular=drive.angular, linear_y=drive.linear_y)
