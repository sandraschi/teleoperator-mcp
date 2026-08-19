"""Authority state per actuator group."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TeleopMode = Literal["DIRECT", "AUTO", "SHARED"]
GroupName = Literal["base", "gaze", "manip"]

ALL_GROUPS: tuple[GroupName, ...] = ("base", "gaze", "manip")


@dataclass
class GroupAuthority:
    mode: TeleopMode = "DIRECT"
    owner: str = "human_pose"


@dataclass
class AuthorityState:
    base: GroupAuthority = field(default_factory=GroupAuthority)
    gaze: GroupAuthority = field(default_factory=GroupAuthority)
    manip: GroupAuthority = field(default_factory=lambda: GroupAuthority(owner="human_pose"))
    estop_latched: bool = False

    def group(self, name: GroupName) -> GroupAuthority:
        return getattr(self, name)

    def set_group(self, name: GroupName, auth: GroupAuthority) -> None:
        setattr(self, name, auth)

    def to_dict(self) -> dict:
        return {
            "base": {"mode": self.base.mode, "owner": self.base.owner},
            "gaze": {"mode": self.gaze.mode, "owner": self.gaze.owner},
            "manip": {"mode": self.manip.mode, "owner": self.manip.owner},
            "estop_latched": self.estop_latched,
        }
