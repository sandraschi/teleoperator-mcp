"""Noetix Bumi humanoid adapter via bumi-mcp REST."""

from __future__ import annotations

import httpx

from ..config import settings
from ..gaze_bumi import BumiHeadFollower
from ..mappers.bumi import BumiMapper, HeadCommand, WalkCommand
from ..types import BaseCommand, GazeCommand, ProducerCommand, RobotCapabilities
from .base import RobotAdapter


class BumiAdapter(RobotAdapter):
    """Sink for Bumi: walk (legs) + head gaze. Manip when pose frame includes hands."""

    def __init__(self, mapper: BumiMapper | None = None) -> None:
        self._mapper = mapper or BumiMapper()
        self._gaze = BumiHeadFollower(self._mapper)

    @property
    def capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_id="bumi",
            display_name="Noetix Bumi (humanoid)",
            has_base=True,
            has_legs=True,
            balance_risk=True,
            has_arms=True,
            hand_type="gripper",
            programmable=True,
        )

    @property
    def api_base(self) -> str:
        return settings.bumi_api_url.rstrip("/")

    async def apply_gaze(self, gaze: GazeCommand, client: httpx.AsyncClient) -> bool:
        cmd = HeadCommand(yaw_deg=gaze.pan, pitch_deg=gaze.tilt)
        ok = await self._mapper.apply_head(cmd, client)
        if ok:
            self._gaze.remember(gaze.pan, gaze.tilt)
        return ok

    async def apply(self, command: ProducerCommand, client: httpx.AsyncClient) -> None:
        if command.base is not None:
            walk = WalkCommand(linear=command.base.linear, angular=command.base.angular)
            await self._mapper.apply_walk(walk, client)
        if command.gaze is not None:
            await self.apply_gaze(command.gaze, client)
        if command.manip is not None:
            await self._mapper.apply_manip(command.manip, client)

    async def e_stop(self, client: httpx.AsyncClient) -> None:
        await self._mapper.e_stop(client)

    @staticmethod
    def gaze_from_head(head: dict) -> GazeCommand:
        mapped = BumiMapper().map_head(head)
        return GazeCommand(pan=mapped.yaw_deg, tilt=mapped.pitch_deg)

    def gaze_from_head_follow(self, head: dict) -> GazeCommand | None:
        return self._gaze.from_head(head)

    @staticmethod
    def base_from_controller(right: dict) -> BaseCommand:
        walk = BumiMapper().map_walk(right)
        return BaseCommand(linear=walk.linear, angular=walk.angular, linear_y=0.0)
