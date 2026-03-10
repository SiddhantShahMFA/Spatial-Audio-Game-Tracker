"""Normalized replay data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlayerState:
    player_id: str
    team: str
    x: float
    z: float
    y: float = 0.0
    distance_to_ball: float | None = None


@dataclass(slots=True)
class Frame:
    frame_id: int
    period: int
    timestamp_s: float
    ball_x: float
    ball_z: float
    ball_y: float = 0.0
    ball_speed_mps: float = 0.0
    players: list[PlayerState] = field(default_factory=list)
    possessing_team: str | None = None
    nearest_attacker_id: str | None = None
    nearest_defender_id: str | None = None
    event_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MatchEvent:
    event_id: str
    frame_id: int
    timestamp_s: float
    team: str
    event_type: str
    subtype: str | None
    player_from: str | None
    player_to: str | None
    x: float | None
    z: float | None
    raw_x: float | None
    raw_y: float | None
    important: bool
    narration_priority: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReplayBundle:
    source_name: str
    fps: float
    frames: list[Frame]
    events: list[MatchEvent]

    @property
    def duration_s(self) -> float:
        if not self.frames:
            return 0.0
        return self.frames[-1].timestamp_s
