"""Per-group authority arbiter — merges producer commands for the robot adapter."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from ..adapters.base import RobotAdapter
from ..producers.human_pose import HumanPoseProducer
from ..producers.nav_stub import NavStubProducer
from ..types import BaseCommand, GazeCommand, ProducerCommand, RobotCapabilities, groups_from_capabilities
from .state import ALL_GROUPS, AuthorityState, GroupAuthority, GroupName, TeleopMode

logger = logging.getLogger("teleoperator_mcp.arbiter")

HUMAN_ID = "human_pose"
NAV_STUB_ID = "nav_stub"


@dataclass
class ResolvedCommand:
    command: ProducerCommand
    sources: dict[str, str]


class AuthorityArbiter:
    def __init__(
        self,
        adapter: RobotAdapter,
        human: HumanPoseProducer | None = None,
        nav_stub: NavStubProducer | None = None,
    ) -> None:
        self.adapter = adapter
        self.human = human or HumanPoseProducer()
        self.nav_stub = nav_stub or NavStubProducer()
        self.capabilities = adapter.capabilities
        self.groups = groups_from_capabilities(self.capabilities)
        self.state = AuthorityState()
        self._last_human = ProducerCommand(producer_id=HUMAN_ID)
        self._last_applied: ProducerCommand | None = None

    def _group_allowed(self, group: GroupName) -> bool:
        return getattr(self.groups, group, False)

    def set_mode(self, group: GroupName, mode: TeleopMode) -> dict:
        if not self._group_allowed(group):
            raise ValueError(f"Group '{group}' not available on {self.capabilities.robot_id}")
        if group == "manip" and not self.capabilities.has_arms:
            raise ValueError("manip group not available — no arms")
        owner = NAV_STUB_ID if mode == "AUTO" else HUMAN_ID
        if mode == "AUTO" and group == "base":
            self.nav_stub.reset_plan()
        self.state.set_group(group, GroupAuthority(mode=mode, owner=owner))
        self.state.estop_latched = False
        logger.info("arbiter set_mode %s=%s owner=%s", group, mode, owner)
        return {"group": group, "mode": mode, "owner": owner}

    def takeover(self, group: GroupName | None = None) -> dict:
        """Human reclaims authority (squeeze / MCP). Clears estop latch."""
        targets: list[GroupName] = [group] if group else [g for g in ALL_GROUPS if self._group_allowed(g)]
        if self._last_applied is not None:
            self._last_human = ProducerCommand(
                producer_id=HUMAN_ID,
                base=self._last_applied.base,
                gaze=self._last_applied.gaze,
                manip=self._last_applied.manip,
            )
        for g in targets:
            self.state.set_group(g, GroupAuthority(mode="DIRECT", owner=HUMAN_ID))
        self.state.estop_latched = False
        logger.info("arbiter takeover groups=%s", targets)
        return {"takeover": targets, "estop_latched": False}

    def any_auto(self) -> bool:
        for g in ALL_GROUPS:
            if not self._group_allowed(g):
                continue
            if self.state.group(g).mode == "AUTO":
                return True
        return False

    def update_human(self, command: ProducerCommand) -> None:
        self._last_human = command

    def _resolve_group_base(self) -> tuple[BaseCommand | None, str]:
        auth = self.state.base
        if auth.mode == "AUTO" and auth.owner == NAV_STUB_ID:
            cmd = self.nav_stub.tick()
            return cmd.base, NAV_STUB_ID
        return self._last_human.base, HUMAN_ID

    def _resolve_group_gaze(self) -> tuple[GazeCommand | None, str]:
        auth = self.state.gaze
        if auth.mode == "AUTO":
            return None, auth.owner
        return self._last_human.gaze, HUMAN_ID

    def resolve(self) -> ResolvedCommand:
        base, base_src = self._resolve_group_base()
        gaze, gaze_src = self._resolve_group_gaze()
        manip = None
        manip_src = "none"
        if self._group_allowed("manip") and self.state.manip.mode == "AUTO":
            manip_src = self.state.manip.owner
        elif self._last_human.manip is not None:
            manip = self._last_human.manip
            manip_src = HUMAN_ID

        merged = ProducerCommand(
            producer_id="arbiter",
            base=base,
            gaze=gaze,
            manip=manip,
        )
        sources = {"base": base_src, "gaze": gaze_src, "manip": manip_src}
        self._last_applied = merged
        return ResolvedCommand(command=merged, sources=sources)

    async def apply_resolved(self, http_client: httpx.AsyncClient) -> ResolvedCommand:
        if self.state.estop_latched:
            await self.adapter.e_stop(http_client)
            return ResolvedCommand(
                command=ProducerCommand(producer_id="arbiter"),
                sources={"base": "estop", "gaze": "estop", "manip": "estop"},
            )
        resolved = self.resolve()
        await self.adapter.apply(resolved.command, http_client)
        return resolved

    async def estop(self, http_client: httpx.AsyncClient) -> None:
        self.state.estop_latched = True
        await self.adapter.e_stop(http_client)

    def status(self) -> dict:
        return {
            "authority": self.state.to_dict(),
            "groups_available": {
                "base": self.groups.base,
                "gaze": self.groups.gaze,
                "manip": self.groups.manip,
            },
            "any_auto": self.any_auto(),
            "last_applied": {
                "base": self._last_applied.base.__dict__ if self._last_applied and self._last_applied.base else None,
                "gaze": self._last_applied.gaze.__dict__ if self._last_applied and self._last_applied.gaze else None,
            }
            if self._last_applied
            else None,
        }
